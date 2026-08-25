"""
UR5 sample-changer plans
========================

Bluesky port of the caproto ``SamplesGroup`` sample-changer IOC. The robot
picks a sample holder off the board, travels a fixed waypoint path to the
Aerotech stage, and places it (and the reverse). Drives the
:class:`mcp_instrument.devices.ur5_robot.UR5` device: ``ur5.pose`` performs a
linear Cartesian move (``moveL``) and ``ur5.gripper`` grabs/releases.

The IOC's stateful bookkeeping does *not* translate to a stateless plan and is
intentionally omitted: labjack presence sensing, autosave PVs,
``current_sample`` tracking, and the camera/dashboard ``cal_stage`` calibration
(which reads ``.urp`` programs the UR5 device does not expose). The caller is
responsible for the stage being empty before ``load_sample`` and occupied
before ``unload_sample``; pass an explicit ``stage_position`` once it has been
calibrated, otherwise the nominal :data:`STAGE_POSITION` is used.

.. autosummary::
    ~load_sample
    ~unload_sample
    ~home_robot
"""

import logging

import numpy as np
from bluesky import plan_stubs as bps

logger = logging.getLogger(__name__)


# -- Geometry (from the SamplesGroup IOC) -----------------------------------

# Nominal Aerotech stage pose. On the real system the (x, y, z) is measured by
# the camera calibration; here it is the nominal value plus the camera offset.
XYZ_STAGE = [0.20354, -0.41995, -0.06055]
RXYZ_STAGE = [-2.893, -1.226, -0.003]
# Offset accounting for the camera not being centered on the robot.
STAGE_DELTA = [0.00499, 0.00105, 0, 0, 0, 0]
STAGE_POSITION = [a + b for a, b in zip(XYZ_STAGE + RXYZ_STAGE, STAGE_DELTA)]

# 24 sample holders arranged in a 6-wide grid on the board.
xyz8 = [-0.07709, 0.35717, 0.06101]
xyz22 = [0.07552, 0.20068, 0.06088]
x_del = (xyz22[0] - xyz8[0]) / 2
y_del = (xyz8[1] - xyz22[1]) / 2
pos15 = (np.array(xyz8) + np.array(xyz22)) / 2
pos0 = [pos15[0] - 3 * x_del, pos15[1] + 2 * y_del, pos15[2]]
Rxyz0 = [-2.244, 2.2, 0.009]

SAMPLE_POSITIONS = []
for _n in range(24):
    _x = pos0[0] + _n % 6 * x_del
    _y = pos0[1] - _n // 6 * y_del
    SAMPLE_POSITIONS.append([_x, _y, pos15[2]] + Rxyz0)

# Safe travel path between the board and the stage. Each waypoint is (x, y, z)
# only; the orientation is filled in with TRAVEL_RXYZ (the board orientation the
# IOC's ``home`` used when padding these same waypoints).
BOARD_TO_STAGE_PATH = [
    [-0.26949, 0.10510, 0.41805],
    [-0.04074, -0.40701, 0.31061],
]
TRAVEL_RXYZ = [2.242, -2.199, -0.008]

# Gripper is lifted 0.2 m above the stage position (used by cal_stage on the
# real system; kept here for reference).
Z_GRIPPER_STAGE = 0.2


# -- Motion helpers ---------------------------------------------------------

def _as_pose6(pose):
    """Return a 6-vector (x, y, z, rx, ry, rz), padding 3-vectors with the
    travel orientation."""
    pose = list(pose)
    if len(pose) == 3:
        return pose + TRAVEL_RXYZ
    if len(pose) == 6:
        return pose
    raise ValueError(f"pose must have 3 or 6 elements, got {len(pose)}")


def _sample_position(sample):
    """Resolve *sample* to a 6-vector: an int indexes SAMPLE_POSITIONS, a
    sequence is used as an explicit pose."""
    if isinstance(sample, int):
        return SAMPLE_POSITIONS[sample]
    return list(sample)


def move_l(ur5, pose):
    """Linear Cartesian move to *pose* (the IOC's ``driver.movel``)."""
    yield from bps.mv(ur5.pose, tuple(_as_pose6(pose)))


def pick(ur5, pose):
    """Move to *pose* and close the gripper on the holder (``driver.pickl``)."""
    yield from move_l(ur5, pose)
    yield from bps.mv(ur5.gripper, "closed")


def place(ur5, pose):
    """Move to *pose* and release the holder (``driver.placel``)."""
    yield from move_l(ur5, pose)
    yield from bps.mv(ur5.gripper, "open")


# -- Sample-changer plans ---------------------------------------------------

def load_sample(ur5, sample, stage_position=None, waypoints=None):
    """Load a sample from the board onto the stage.

    Mirrors ``SampleGroup.load``: pick the holder off the board, traverse the
    waypoints toward the stage, place it, then retreat along the waypoints in
    reverse to a safe resting pose.

    Parameters
    ----------
    sample
        Board index (0-23 into :data:`SAMPLE_POSITIONS`) or an explicit
        (x, y, z, rx, ry, rz) board pose.
    stage_position
        Calibrated stage pose; defaults to :data:`STAGE_POSITION`.
    waypoints
        Board-to-stage travel path; defaults to :data:`BOARD_TO_STAGE_PATH`.
    """
    logger.debug("load_sample(%r)", sample)
    sample_position = _sample_position(sample)
    stage_position = STAGE_POSITION if stage_position is None else stage_position
    waypoints = BOARD_TO_STAGE_PATH if waypoints is None else waypoints

    yield from pick(ur5, sample_position)
    for waypoint in waypoints:
        yield from move_l(ur5, waypoint)
    yield from place(ur5, stage_position)
    for waypoint in reversed(waypoints):
        yield from move_l(ur5, waypoint)


def unload_sample(ur5, sample, stage_position=None, waypoints=None):
    """Return a sample from the stage to its board position.

    Mirrors ``SampleGroup.unload``: traverse the waypoints to the stage, pick
    the holder off the stage, retreat along the waypoints in reverse, place it
    back on the board, then rest at the first waypoint.

    Parameters
    ----------
    sample
        Board index (0-23) or explicit board pose to return the holder to.
    stage_position
        Calibrated stage pose; defaults to :data:`STAGE_POSITION`.
    waypoints
        Board-to-stage travel path; defaults to :data:`BOARD_TO_STAGE_PATH`.
    """
    logger.debug("unload_sample(%r)", sample)
    sample_position = _sample_position(sample)
    stage_position = STAGE_POSITION if stage_position is None else stage_position
    waypoints = BOARD_TO_STAGE_PATH if waypoints is None else waypoints

    for waypoint in waypoints:
        yield from move_l(ur5, waypoint)
    yield from pick(ur5, stage_position)
    for waypoint in reversed(waypoints):
        yield from move_l(ur5, waypoint)
    yield from place(ur5, sample_position)
    yield from move_l(ur5, waypoints[0])


def home_robot(ur5, waypoints=None):
    """Send the robot to its home/rest pose near the board.

    Mirrors ``SamplesGroup.home``: if the arm is currently out toward the stage
    (past the last waypoint in y), retreat through the waypoints in reverse;
    otherwise go straight to the board-side waypoint.

    Parameters
    ----------
    waypoints
        Board-to-stage travel path; defaults to :data:`BOARD_TO_STAGE_PATH`.
    """
    logger.debug("home_robot()")
    waypoints = BOARD_TO_STAGE_PATH if waypoints is None else waypoints
    poses = [_as_pose6(waypoint) for waypoint in waypoints]

    if ur5.pose_y_readback.get() < poses[-1][1]:
        for pose in reversed(poses):
            yield from move_l(ur5, pose)
    else:
        yield from move_l(ur5, poses[0])
