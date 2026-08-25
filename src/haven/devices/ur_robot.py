"""UR robotic arm control device.
"""
import time
from ophyd import Component
from ophyd import Device, DeviceStatus
from ophyd import PVPositionerPC
from ophyd import DerivedSignal
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd.status import Status
from ophyd.status import SubscriptionStatus
import numpy as np
from enum import Enum

class GripperState(Enum):
    OPEN = 0
    CLOSE = 1

class _URRobotiqGripperGroup(Device):
    open = Component(EpicsSignal, "RobotiqGripper:Open")
    close = Component(EpicsSignal, "RobotiqGripper:Close")

    # String aliases accepted by set() (e.g. from bps.mv).
    _str_to_state = {
        "open": GripperState.OPEN,
        "close": GripperState.CLOSE,
        "closed": GripperState.CLOSE,
    }

    def set(self, target, timeout=None):
        if isinstance(target, str):
            try:
                target = self._str_to_state[target.lower()]
            except KeyError:
                raise ValueError(
                    f"gripper target must be a GripperState or one of "
                    f"{sorted(self._str_to_state)}, got {target!r}"
                ) from None
        status = DeviceStatus(self, timeout=timeout)
        done_callback = lambda **kwargs: status.set_finished()
        if target == GripperState.OPEN:
            self.open.put(1, wait=False, callback=done_callback)
        elif target == GripperState.CLOSE:
            self.close.put(1, wait=False, callback=done_callback)
        else:
            raise ValueError("target must be GripperState.OPEN or GripperState.CLOSE")

        return status

    def set_close(self):
        status = self.set(GripperState.CLOSE)
        return status

    def set_open(self):
        status = self.set(GripperState.OPEN)
        return status

class _URPoseGroup(Device):
    x_setpoint = Component(EpicsSignal, 'Control:PoseXCmd', kind='omitted')
    y_setpoint = Component(EpicsSignal, 'Control:PoseYCmd', kind='omitted')
    z_setpoint = Component(EpicsSignal, 'Control:PoseZCmd', kind='omitted')
    rx_setpoint = Component(EpicsSignal, 'Control:PoseRxCmd', kind='omitted')
    ry_setpoint = Component(EpicsSignal, 'Control:PoseRyCmd', kind='omitted')
    rz_setpoint = Component(EpicsSignal, 'Control:PoseRzCmd', kind='omitted')
    readback = Component(EpicsSignalRO, 'Receive:ActualTCPPose', kind='hinted')
    move_trigger = Component(EpicsSignal, 'Control:moveL', kind='omitted')

    def set(self, target, *, timeout=None, **kwargs):
        """Set all 6 TCP positions

        Parameters
        ----------
        target : array-like
            6-element sequence of TCP positions
        timeout : float, optional
            Maximum time to wait for move completion
        """
        targets = tuple(target)
        if len(targets) != 6:
            raise ValueError(f"Expected 6 joint values, got {len(targets)}")

        # Write all setpoints
        for cpt, val in zip(
            (self.x_setpoint, self.y_setpoint, self.z_setpoint,
             self.rx_setpoint, self.ry_setpoint, self.rz_setpoint),
            targets
        ):
            cpt.put(val)

        # Create status and trigger move with put completion
        status = DeviceStatus(self, timeout=timeout)
        def done_callback(**kwargs):
            status.set_finished()
        self.move_trigger.put(1, wait=False, callback=done_callback)

        return status

class _URJointGroup(Device):
    """Multi-axis joint positioner with put completion on move trigger.

    set((j1, j2, j3, j4, j5, j6)) writes all six setpoints and triggers
    the move. Returns a Status that completes via put completion callback
    from the busy record.
    """

    # Setpoints
    j1_setpoint = Component(EpicsSignal, 'Control:J1Cmd', kind='omitted')
    j2_setpoint = Component(EpicsSignal, 'Control:J2Cmd', kind='omitted')
    j3_setpoint = Component(EpicsSignal, 'Control:J3Cmd', kind='omitted')
    j4_setpoint = Component(EpicsSignal, 'Control:J4Cmd', kind='omitted')
    j5_setpoint = Component(EpicsSignal, 'Control:J5Cmd', kind='omitted')
    j6_setpoint = Component(EpicsSignal, 'Control:J6Cmd', kind='omitted')
    readback = Component(EpicsSignalRO, 'Receive:ActualJointPositions', kind='hinted')
    move_trigger = Component(EpicsSignal, 'Control:moveJ', kind='omitted')

    def set(self, target, *, timeout=None, **kwargs):
        """Set all 6 joint positions

        Parameters
        ----------
        target : array-like
            6-element sequence of joint positions
        timeout : float, optional
            Maximum time to wait for move completion
        """
        targets = tuple(target)
        if len(targets) != 6:
            raise ValueError(f"Expected 6 joint values, got {len(targets)}")

        # Write all setpoints
        for cpt, val in zip(
            (self.j1_setpoint, self.j2_setpoint, self.j3_setpoint,
             self.j4_setpoint, self.j5_setpoint, self.j6_setpoint),
            targets
        ):
            cpt.put(val)

        # Create status and trigger move with put completion
        status = DeviceStatus(self, timeout=timeout)

        def done_callback(**kwargs):
            status.set_finished()

        self.move_trigger.put(1, wait=False, callback=done_callback)

        return status


class _TCPAxisSignal(DerivedSignal):
    """Read-only scalar view onto one axis of the TCP pose array.

    ``derived_from`` may be a dotted attribute path relative to the parent
    device (e.g. ``"pose.readback"``), so a single element of the nested
    ``ActualTCPPose`` array can be exposed at the top level.
    """

    def __init__(self, derived_from, *, axis, parent=None, **kwargs):
        self._axis = axis
        if isinstance(derived_from, str):
            obj = parent
            for part in derived_from.split("."):
                obj = getattr(obj, part)
            derived_from = obj
        super().__init__(derived_from, parent=parent, **kwargs)

    def inverse(self, value):
        return value[self._axis]


class UR(Device):
    """Universal Robots e-series arm exposed via the urRobot EPICS support module."""

    moving = Component(EpicsSignal, "Control:Moving")
    stop_robot = Component(EpicsSignal, "Control:Stop.PROC", kind="omitted")
    gripper = Component(_URRobotiqGripperGroup, "")
    joints = Component(_URJointGroup, "")
    pose = Component(_URPoseGroup, "")
    pose_y_readback = Component(
        _TCPAxisSignal, derived_from="pose.readback", axis=1, kind="omitted"
    )