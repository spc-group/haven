"""
UR5 sample-changer plans
========================

Bluesky translation of the caproto ``SamplesGroup`` sample-changer IOC. A UR5
robot moves a sample holder between a board of 24 holders and the Aerotech
stage, following a fixed set of waypoints so the arm travels a known, safe path.

Each plan takes the ``ur5`` device (:class:`haven.devices.ur_robot.UR`) as its
first argument and drives just two of its parts:

* ``ur5.pose`` -- a linear Cartesian move (``moveL``) to a 6-element
  ``(x, y, z, rx, ry, rz)`` pose,
* ``ur5.gripper`` -- ``"closed"`` to grab a holder, ``"open"`` to release it.

The IOC's stateful bookkeeping is intentionally left out because it does not fit
a stateless plan (and the ``ur5`` device does not expose the hardware for it):
labjack presence sensing, ``current_sample`` tracking, and the ``cal_stage``
camera calibration (which plays ``.urp`` programs through a dashboard). The
caller is therefore responsible for the stage being empty before
:func:`load_sample` and occupied before :func:`unload_sample`, and for passing a
calibrated ``stage`` pose once one is known (otherwise the nominal
:data:`STAGE_POSITION` is used).

.. autosummary::
    ~load_sample
    ~unload_sample
    ~home_robot
"""

import logging

from bluesky import plan_stubs as bps

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Geometry (transcribed from the caproto SamplesGroup IOC)
# ---------------------------------------------------------------------------
# Every pose is ``(x, y, z, rx, ry, rz)``: millimetres for position and
# rotation-vector radians for orientation, in the robot's base frame.

# Aerotech stage. On the real system the (x, y, z) is measured by the camera
# calibration (``cal_stage``); here the nominal survey value plus the camera
# offset is used as a sensible default.
# _STAGE_XYZ = [203.54, -419.95, -60.55]
# _STAGE_RXYZ = [-2.893, -1.226, -0.003]
_STAGE_XYZ = [148.04, -434.11, 140.38+22]
_STAGE_RXYZ = [-2.893, -1.226, -0.003]
# _CAMERA_OFFSET = [4.99, 1.05, 0.0, 0.0, 0.0, 0.0]
_CAMERA_OFFSET = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
STAGE_POSITION = [
    coord + offset for coord, offset in zip(_STAGE_XYZ + _STAGE_RXYZ, _CAMERA_OFFSET)
]

# Sample board: 24 holders in a 6-wide grid, sharing one orientation. The grid
# is reconstructed from two surveyed holders (#8 and #22); #15 is their midpoint
# and holder #0 sits three columns left and two rows up from it.
# _XYZ_8 = [-77.09, 357.17, 61.01]
_XYZ_8 = [-100.58, 359.30, 271+24]
# _XYZ_22 = [75.52, 200.68, 60.88]
_XYZ_22 = [50.07, 202.28, 271+24]
_HOLDER_RXYZ = [-2.244, 2.2, 0.009]
_COLUMN_STEP = (_XYZ_22[0] - _XYZ_8[0]) / 2  # x spacing between adjacent columns
_ROW_STEP = (_XYZ_8[1] - _XYZ_22[1]) / 2  # y spacing between adjacent rows
_center = [(a + b) / 2 for a, b in zip(_XYZ_8, _XYZ_22)]  # holder #15
_holder0 = [_center[0] - 3 * _COLUMN_STEP, _center[1] + 2 * _ROW_STEP, _center[2]]

SAMPLE_POSITIONS = []
for _n in range(24):
    _x = _holder0[0] + (_n % 6) * _COLUMN_STEP
    _y = _holder0[1] - (_n // 6) * _ROW_STEP
    SAMPLE_POSITIONS.append([_x, _y, _holder0[2]] + _HOLDER_RXYZ)

# Safe travel path between the board and the stage, ordered board side first.
# The IOC stored these as (x, y, z) only and moved with the fixed travel
# orientation below; the ur5 device's moveL needs a full 6-DOF pose, so the
# orientation is padded on here.
# _TRAVEL_RXYZ = [2.242, -2.199, -0.008]
_TRAVEL_RXYZ = [-2.242, 2.199, 0.008]
BOARD_TO_STAGE = [
    #[-264.89, -116.25, 418.02, *_TRAVEL_RXYZ],
    [-269.49, 105.10, 418.05, *_TRAVEL_RXYZ],
    # [-269.49, 105.10, 418.05] + _TRAVEL_RXYZ,  # board side
    [-40.74, -407.01, 310.61] + _TRAVEL_RXYZ,  # stage side
]


# ---------------------------------------------------------------------------
# Low-level robot motions
# ---------------------------------------------------------------------------

def move_to(ur5, pose):
    """Linear Cartesian move (``moveL``) to a 6-element pose."""
    yield from bps.mv(ur5.pose, tuple(pose))


def grab(ur5):
    """Close the gripper onto a holder (the IOC's ``pick``)."""
    yield from bps.mv(ur5.gripper, "closed")


def release(ur5):
    """Open the gripper to let go of a holder (the IOC's ``place``)."""
    yield from bps.mv(ur5.gripper, "open")


def board_pose(sample):
    """Resolve *sample* to a 6-element pose.

    An ``int`` indexes the board grid (0-23); any other sequence is taken as an
    explicit ``(x, y, z, rx, ry, rz)`` pose.
    """
    if isinstance(sample, int):
        return SAMPLE_POSITIONS[sample]
    return list(sample)


# Approach offset applied to a pick/place target to get the safe "above" pose
# the arm passes through before descending onto a holder (and lifts back to
# after the gripper acts). x/y/z are millimetres, rx/ry/rz are radians.
# _ABOVE_OFFSET = [0.0, -76.2, 134.0, 0.103, -0.104, 0.151]
_ABOVE_OFFSET = [0.0, 0.0, 134.0, 0.0, 0.0, 0.0]


def above_pose(pose):
    """Return the safe approach pose above a pick/place *pose*."""
    return [coord + offset for coord, offset in zip(pose, _ABOVE_OFFSET)]


# ---------------------------------------------------------------------------
# Sample-changer plans
# ---------------------------------------------------------------------------

def load_sample(ur5, sample, stage=None):
    """Move a sample holder from the board onto the stage.

    Mirrors ``SampleGroup.load``.

    Parameters
    ----------
    sample
        Board grid index (0-23) or an explicit ``(x, y, z, rx, ry, rz)`` pose.
    stage
        Where to place the holder; defaults to :data:`STAGE_POSITION`. Pass the
        calibrated stage pose once it is known.
    """
    log.debug("load_sample(%r)", sample)
    board = board_pose(sample)
    stage = STAGE_POSITION if stage is None else stage
    yield from home_robot(ur5)
    # 1. Pick the holder up off the board.
    yield from move_to(ur5, above_pose(board))
    yield from move_to(ur5, board)
    yield from grab(ur5)
    yield from move_to(ur5, above_pose(board))
    # 2. Carry it out to the stage along the safe path.
    for waypoint in BOARD_TO_STAGE:
        yield from move_to(ur5, waypoint)
    # 3. Set it down on the stage.
    yield from move_to(ur5, above_pose(stage))
    yield from move_to(ur5, stage)
    yield from release(ur5)
    yield from move_to(ur5, above_pose(stage))
    # 4. Retreat back along the path to a resting pose.
    for waypoint in reversed(BOARD_TO_STAGE):
        yield from move_to(ur5, waypoint)


def unload_sample(ur5, sample, stage=None):
    """Return a sample holder from the stage to its board position.

    Mirrors ``SampleGroup.unload``.

    Parameters
    ----------
    sample
        Board grid index (0-23) or an explicit ``(x, y, z, rx, ry, rz)`` pose to
        return the holder to.
    stage
        Where to pick the holder up from; defaults to :data:`STAGE_POSITION`.
    """
    log.debug("unload_sample(%r)", sample)
    board = board_pose(sample)
    stage = STAGE_POSITION if stage is None else stage

    # # 1. Travel out to the stage along the safe path.
    yield from home_robot(ur5)

    # for waypoint in BOARD_TO_STAGE:
    #     yield from move_to(ur5, waypoint)
    # 2. Pick the holder up off the stage.
    yield from move_to(ur5, above_pose(stage))
    yield from move_to(ur5, stage)
    yield from grab(ur5)
    yield from move_to(ur5, above_pose(stage))
    # 3. Retreat back along the path.
    for waypoint in reversed(BOARD_TO_STAGE):
        yield from move_to(ur5, waypoint)
    # 4. Set the holder back down on the board.
    yield from move_to(ur5, above_pose(board))
    yield from move_to(ur5, board)
    yield from release(ur5)
    yield from move_to(ur5, above_pose(board))
    # 5. Rest at the board-side waypoint.
    yield from move_to(ur5, BOARD_TO_STAGE[0])


def home_robot(ur5):
    """Send the arm to its rest pose near the board.

    Mirrors ``SamplesGroup.home``: if the arm is currently out toward the stage
    (past the stage-side waypoint in y), retreat through the waypoints in
    reverse; otherwise go straight to the board-side waypoint.
    """
    log.debug("home_robot()")
    stage_side = BOARD_TO_STAGE[-1]
    if ur5.pose_y_readback.get() < stage_side[1]:
        for waypoint in reversed(BOARD_TO_STAGE):
            yield from move_to(ur5, waypoint)
    else:
        yield from move_to(ur5, BOARD_TO_STAGE[0])

def move_to_stage(ur5):
    """Move the robot to the stage position."""
    log.debug("move_to_stage()")
    for waypoint in BOARD_TO_STAGE:
        yield from move_to(ur5, waypoint)
