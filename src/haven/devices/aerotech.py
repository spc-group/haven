import asyncio
import logging

import numpy as np
import pint
from ophyd_async.core import (
    CALCULATE_TIMEOUT,
    DEFAULT_TIMEOUT,
    Array1D,
    AsyncStatus,
    DetectorTrigger,
    DeviceVector,
    StandardReadable,
    StandardReadableFormat,
    StrictEnum,
    error_if_none,
    observe_value,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_x
from scanspec.core import Path

from haven import exceptions
from haven.devices.motor import Motor

log = logging.getLogger(__name__)

ureg = pint.UnitRegistry()


"""
An example script written by Kevin, for dev reference.

```python

#!/APSshare/anaconda3/x86_64/bin/python
#/usr/bin/env python3

import math
import epics

numPoints = 101
startPos = -1000
endPos = 1000
segmentSize = (endPos - startPos) / (numPoints - 1)

#
m1pos = list(range(startPos, endPos+1, int(segmentSize)))

epics.caput("25idc:pm1:NumPoints", numPoints)
epics.caput("25idc:pm1:NumPulses", numPoints)
epics.caput("25idc:pm1:StartPulses", 0)
epics.caput("25idc:pm1:EndPulses", numPoints)

#!epics.caput("25idc:pm1:FixedTime", 1.0)
#!epics.caput("25idc:pm1:Acceleration", 0.5)

epics.caput("25idc:pm1:M2Positions", m1pos)
# Is this necessary for fixed time mode scans?
epics.caput("25idc:pm1:PulsePositions", m1pos)

#!epics.caput("25idc:pm1:M1UseAxis", 1)

#!epics.caput("25idc:pm1:MoveMode", "Absolute")

```

"""


class AerotechMotor(Motor):
    """Allow an Aerotech stage to fly-scan via the Ophyd FlyerInterface.

    Set *start_position*, *end_position*, and *step_size* in units of
    the motor record (.EGU), and *dwell_time* in seconds. Then the
    remaining components will be calculated accordingly.

    All position or distance components are assumed to be in motor
    record engineering units, unless preceded with "encoder_", in
    which case they are in units of encoder pulses based on the
    encoder resolution.

    The following diagram describes how the various components relate
    to each other. Distances are not to scale::

                 ┌─ encoder_window_start         ┌─ encoder_window_stop
                 │                               │
                 │ |┄┄┄| *step_size*             │
                 │ │   │ encoder_step_size       │
                 │ │   │                         │
      Window:    ├┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┤

      Pulses: ┄┄┄┄┄╨───╨───╨───╨───╨───╨───╨───╨┄┄┄┄┄
               │   │ │                       │ │   └─ taxi_end
               │   │ └─ *start_position*     │ └─ pso_end
               │   └─ pso_start              └─ *end position*
               └─ taxi_start

    Parameters
    ==========
    axis
      The label used by the aerotech controller to refer to this
      axis. Examples include "@0" or "X".
    encoder
      The number of the encoder to track when fly-scanning with this
      device.

    Components
    ==========
    start_position
      User-requested center of the first scan pixel.
    end_position
      User-requested center of the last scan pixel. This is not
      guaranteed and may be adjusted to match the encoder resolution
      of the stage.
    step_size
      How much space desired between points. This is not guaranteed
      and may be adjusted to match the encoder resolution of the
      stage.
    dwell_time
      How long to take, in seconds, moving between points.
    slew_speed
      How fast to move the stage. Calculated from the remaining
      components.
    taxi_start
      The starting point for motor movement during flying, accounts
      for needed acceleration of the motor.
    taxi_end
      The target point for motor movement during flying, accounts
      for needed acceleration of the motor.
    pso_start
      The motor position corresponding to the first PSO pulse.
    pso_end
      The motor position corresponding to the last PSO pulse.
    encoder_step_size
      The number of encoder counts for each pixel.
    encoder_window_start
      The start of the window within which PSO pulses may be emitted,
      in encoder counts. Should be slightly wider than the actual PSO
      range.
    encoder_window_end
      The end of the window within which PSO pulses may be emitted,
      in encoder counts. Should be slightly wider than the actual PSO
      range.

    """

    axis: int
    detector_trigger: DetectorTrigger = DetectorTrigger.EDGE_TRIGGER
    _fly_points = None

    def __init__(self, *args, axis: int, **kwargs):
        super().__init__(*args, **kwargs)
        # Save needed axis/encoder values
        self.axis = axis

    async def prepare_scanspec(self, path: Path):
        # Initial calculations
        stage = self.parent
        points = path.consume()
        self._fly_points = points
        # Get the positions for where the PSO should actually fire
        pulse_points = [
            (lower, upper) if gap else (upper,)
            for lower, upper, gap in zip(
                points.lower[self], points.upper[self], points.gap
            )
        ]
        pulse_positions = np.asarray(
            [pulse for pulses in pulse_points for pulse in pulses]
        )
        num_pulses = len(pulse_positions)
        # Set up profile parameters
        ixce2_output = 143
        dwell_time = np.unique(points.duration)
        if dwell_time.shape == (1,):
            dwell_time = dwell_time[0]
        else:
            raise ValueError(
                f"Aerotech cannot handle non-constant scan durations: {dwell_time}"
            )
        await asyncio.gather(
            stage.profile_move.point_count.set(num_pulses),
            stage.profile_move.pulse_count.set(num_pulses),
            stage.profile_move.pulse_range_start.set(0),
            stage.profile_move.pulse_range_end.set(num_pulses),
            stage.profile_move.move_mode.set(MoveMode.ABSOLUTE),
            stage.profile_move.pulse_direction.set(PulseDirection.BOTH),
            stage.profile_move.axis[self.axis].positions.set(pulse_positions),
            stage.profile_move.pulse_positions.set(pulse_positions),
            # Only enable this axis, disable all others
            *(
                axis.enabled.set(num == self.axis)
                for num, axis in stage.profile_move.axis.items()
            ),
            # We need fixed-time mode for now
            # To-do: sort out how to do array time mode
            stage.profile_move.time_mode.set(TimeMode.FIXED),
            stage.profile_move.dwell_time.set(dwell_time),
            # stage.profile_move.time_mode.set(TimeMode.ARRAY),
            # stage.profile_move.pulse_times.set(points.duration),
        )

    @AsyncStatus.wrap
    async def prepare(self, value: Path):
        """Prepare the detector to execute the profile specified in *value*."""
        ixce2_output = 143
        stage = self.parent
        self._fly_info = value
        # Magic values for the PSO to work
        # TODO: Sort out which of these need to change for different axes
        await asyncio.gather(
            stage.profile_move.pulse_output.set(ixce2_output),
            stage.profile_move.pulse_source.set(0),
            stage.profile_move.pulse_axis.set(0),
            self.prepare_scanspec(value),
        )
        # Go to the first point
        actual_positions, dwell_time, acceleration_time = await asyncio.gather(
            stage.profile_move.pulse_positions.get_value(),
            stage.profile_move.dwell_time.get_value(),
            stage.profile_move.acceleration_time.get_value(),
        )
        step = actual_positions[1] - actual_positions[0]
        taxi_distance = acceleration_time * step / dwell_time / 2
        await self.set(actual_positions[0] - taxi_distance)
        # Build the profile
        await stage.profile_move.build.trigger()
        observations = observe_value(
            stage.profile_move.build_state, done_timeout=DEFAULT_TIMEOUT
        )
        async for current_state in observations:
            if current_state == BuildState.DONE:
                break
        # Confirm the profile build was successful
        status = await stage.profile_move.build_status.get_value()
        if status != BuildStatus.SUCCESS:
            raise exceptions.ProfileFailure(
                f"Profile move build unsuccessful: {status}"
            )

    @AsyncStatus.wrap
    async def kickoff(self):
        """Start a flyer."""
        error_if_none(
            self._fly_info, "Motor must be prepared before attempting to kickoff"
        )
        stage = self.parent
        await stage.profile_move.execute.trigger()
        # Wait for the stage to report it is flying
        observations = observe_value(
            stage.profile_move.execute_state, done_timeout=DEFAULT_TIMEOUT
        )
        async for current_state in observations:
            if current_state == ExecuteState.EXECUTING:
                break

    @AsyncStatus.wrap
    async def complete(self):
        """Wait for flying to be complete.

        This can either be a question ("are you done yet") or a
        command ("please wrap up") to accommodate flyers that have a
        fixed trajectory (ex. high-speed raster scans) or that are
        passive collectors (ex MAIA or a hardware buffer).

        In either case, the returned status object should indicate when
        the device is actually finished flying.

        """
        fly_info = error_if_none(
            self._fly_info, "Motor must be prepared before attempting to kickoff"
        )
        stage = self.parent
        if self._fly_points is not None:
            timeout = np.sum(self._fly_points.duration) + DEFAULT_TIMEOUT
        elif fly_info.timeout == CALCULATE_TIMEOUT:
            timeout = fly_info.time_for_move + DEFAULT_TIMEOUT
        else:
            timeout = fly_info.timeout
        observations = observe_value(
            stage.profile_move.execute_state, done_timeout=timeout
        )
        async for current_state in observations:
            if current_state == ExecuteState.DONE:
                break
        # Check that the move was successful
        status = await stage.profile_move.execute_status.get_value()
        self._fly_points = None
        if status != ExecuteStatus.SUCCESS:
            raise exceptions.ProfileFailure(
                f"Profile move execution unsuccessful: {status}"
            )


class MoveMode(StrictEnum):
    ABSOLUTE = "Absolute"
    RELATIVE = "Relative"


class TimeMode(StrictEnum):
    FIXED = "Fixed"
    ARRAY = "Array"


class PulseDirection(StrictEnum):
    BOTH = "Both"
    POSITIVE = "Pos"
    NEGATIVE = "Neg"


class PulseMode(StrictEnum):
    FIXED = "Fixed"
    ARRAY = "Array"
    TRAJECTORY_POINTS = "TrajPts"
    NONE = "None"


class BuildState(StrictEnum):
    DONE = "Done"
    BUSY = "Busy"


class BuildStatus(StrictEnum):
    UNDEFINED = "Undefined"
    SUCCESS = "Success"
    FAILURE = "Failure"


class ExecuteState(StrictEnum):
    DONE = "Done"
    MOVE_START = "Move start"
    EXECUTING = "Executing"
    FLYBACK = "Flyback"


class ExecuteStatus(StrictEnum):
    UNDEFINED = "Undefined"
    SUCCESS = "Success"
    FAILURE = "Failure"
    ABORT = "Abort"
    TIMEOUT = "Timeout"


class ProfileAxis(StandardReadable):
    """An individual axis in the profile move."""

    def __init__(self, prefix: str, *, name: str = ""):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.enabled = epics_signal_rw(bool, f"{prefix}UseAxis")
            self.positions = epics_signal_rw(Array1D[np.float64], f"{prefix}Positions")
        super().__init__(name=name)


class ProfileMove(StandardReadable):
    """Controller for programming profile moves."""

    def __init__(self, prefix: str, *, axis_count: int, name: str = ""):
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.acceleration_time = epics_signal_rw(float, f"{prefix}Acceleration")
            self.dwell_time = epics_signal_rw(float, f"{prefix}FixedTime")
            self.move_mode = epics_signal_rw(MoveMode, f"{prefix}MoveMode")
            self.time_mode = epics_signal_rw(TimeMode, f"{prefix}TimeMode")
            self.point_count = epics_signal_rw(int, f"{prefix}NumPoints")
            self.pulse_count = epics_signal_rw(int, f"{prefix}NumPulses")
            self.pulse_range_start = epics_signal_rw(int, f"{prefix}StartPulses")
            self.pulse_range_end = epics_signal_rw(int, f"{prefix}EndPulses")
            self.pulse_direction = epics_signal_rw(PulseDirection, f"{prefix}PulseDir")
            self.pulse_mode = epics_signal_rw(PulseMode, f"{prefix}PulseMode")
            self.pulse_length = epics_signal_rw(int, f"{prefix}PulseLength")
            self.pulse_period = epics_signal_rw(int, f"{prefix}PulsePeriod")
            self.pulse_source = epics_signal_rw(int, f"{prefix}PulseSrc")
            self.pulse_output = epics_signal_rw(int, f"{prefix}PulseOut")
            self.pulse_axis = epics_signal_rw(int, f"{prefix}PulseAxis")
        with self.add_children_as_readables():
            self.axis = DeviceVector(
                {i: ProfileAxis(f"{prefix}M{i+1}") for i in range(axis_count)}
            )
        self.pulse_positions = epics_signal_rw(
            Array1D[np.float64], f"{prefix}PulsePositions"
        )
        self.pulse_times = epics_signal_rw(Array1D[np.float64], f"{prefix}Times")
        self.build = epics_signal_x(f"{prefix}Build")
        self.build_state = epics_signal_r(BuildState, f"{prefix}BuildState")
        self.build_status = epics_signal_r(str, f"{prefix}BuildStatus")
        self.execute = epics_signal_x(f"{prefix}Execute")
        self.execute_state = epics_signal_r(ExecuteState, f"{prefix}ExecuteState")
        self.execute_status = epics_signal_r(str, f"{prefix}ExecuteStatus")
        super().__init__(name=name)


class AerotechStage(StandardReadable):
    """An XY stage for an Aerotech stage with fly-scanning capabilities."""

    _ophyd_labels_ = {"stages"}

    def __init__(
        self,
        prefix: str,
        name: str = "",
    ):
        # Axes devices
        with self.add_children_as_readables():
            self.horizontal = AerotechMotor(prefix=f"{prefix}m1", axis=0)
            self.vertical = AerotechMotor(prefix=f"{prefix}m2", axis=1)
            self.profile_move = ProfileMove(f"{prefix}pm1:", axis_count=2)
        super().__init__(name=name)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
