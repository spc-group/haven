import operator
import uuid
from collections import abc
from collections.abc import Generator, Iterable, Mapping, Sequence
from functools import reduce
from typing import Any

import numpy as np
from bluesky import plan_stubs as bps
from bluesky.preprocessors import (
    run_decorator,
    run_wrapper,
    stage_decorator,
    stage_wrapper,
)
from bluesky.protocols import Flyable, HasName, Preparable
from bluesky.utils import Msg
from ophyd_async.core import DetectorTrigger, Device, TriggerInfo
from scanspec.core import Path, SnakedDimension
from scanspec.specs import ConstantDuration, Fly, Line, Spec, Zip

__all__ = ["fly_scan", "grid_fly_scan"]


def declare_streams(
    primary_detectors: Sequence[Device] = (), secondary_detectors: Sequence[Device] = ()
) -> Generator[Msg, Any, None]:
    """Plan stub to declare data streams for bluesky.

    *primary_detectors* will be grouped into a single primary data
    stream, while *secondary_detectors* will each get their own named
    stream.

    """
    # For now, this is broken, we just declare all the streams as independent
    for detector in (*primary_detectors, *secondary_detectors):
        yield from bps.declare_stream(detector, name=detector.name)
    # if len(primary_detectors) > 0:
    #     yield from bps.declare_stream(*primary_detectors, name="primary")
    # for detector in secondary_detectors:
    #     yield from bps.declare_stream(detector, name=detector.name)


def fly_segment(
    detectors: Sequence[Flyable],
    motors: Sequence[Flyable],
    spec: Spec[Flyable],
    flyer_controllers: Sequence[Flyable] = (),
    *,
    start: int = 0,
    num: int | None = None,
    trigger_info: TriggerInfo,
) -> Generator[Msg, Any, None]:
    """A plan stub for fly-scanning a single trajectory.

    Parameters
    ==========
    detectors
      Will be kicked off before the motors begin to move.
    spec
      A scan spec that describes the trajectory to take. Will be
      consumed by this plan.

    """
    # Prepare the detectors, just for this line segment
    prepare_group = uuid.uuid4()
    frames = spec.calculate()
    for motor in motors:
        path = Path(frames, start=start, num=num)
        yield from bps.prepare(motor, path, group=prepare_group, wait=False)
    for controller in flyer_controllers:
        yield from bps.prepare(
            controller, trigger_info, group=prepare_group, wait=False
        )
    for detector in detectors:
        yield from bps.prepare(detector, trigger_info, group=prepare_group, wait=False)
    yield from bps.wait(group=prepare_group)
    yield from declare_streams(secondary_detectors=detectors)
    # Start the detectors before the motors so we know they'll be ready
    for motor in motors:
        yield from bps.monitor(motor, name=motor.name)
    yield from bps.kickoff_all(*detectors, wait=True)
    if len(flyer_controllers) > 0:
        yield from bps.kickoff_all(*flyer_controllers, wait=True)
    yield from bps.kickoff_all(*motors, wait=True)
    # Finish the scan and cleanup
    yield from bps.complete_all(*motors, wait=True)
    if len(flyer_controllers) > 0:
        yield from bps.complete_all(*flyer_controllers, wait=True)
    yield from bps.complete_all(*detectors, wait=True)
    for detector in detectors:
        yield from bps.collect(detector)
    for motor in motors:
        yield from bps.unmonitor(motor)
    yield from bps.checkpoint()


def fly_scan(
    detectors: Sequence[Flyable],
    *args,
    num: int,
    dwell_time: float,
    trigger: DetectorTrigger = DetectorTrigger.INTERNAL,
    flyer_controllers: Sequence[Flyable] = (),
    md: Mapping = {},
) -> Generator[Msg, Any, None]:
    """Do a fly scan with a 'flyer' motor and some 'flyer' detectors.

    Will use external triggering if *delay_generator* is provided.
    Otherwise, internal triggering is used.

    Parameters
    ----------
    detectors
      List of 'readable' objects that support the flyer interface
    *args
      For one dimension, motor, start, stop. In general:

      .. code-block:: python

         motor1, start1, stop1,
         motor2, start2, stop2,
         ...,
         motorN, startN, stopN

      Motors can be any ‘flyable’ object.
    num
      Number of measurements to take.
    dwell_time
      How long, in seconds, for each measurement point.
    trigger
      The trigger mode to use for flying.
    delay_outputs
      If provided, these delay generator outputs will be used to
      coordinate hardware triggering of detectors.
    md
      metadata

    Yields
    ------
    msg
      'prepare', 'kickoff', 'complete, and 'collect' messages

    """
    # For now, the aerotech is producing shorter segments than expected
    trigger_info = TriggerInfo(
        number_of_events=num,
        livetime=dwell_time * 0.85,
        deadtime=dwell_time * 0.15,
        trigger=trigger,
    )
    # Prepare the motor trajectory
    motors = args[0::3]
    starts = args[1::3]
    stops = args[2::3]
    lines = [
        Line(motor, start, stop, num)
        for (motor, start, stop) in zip(motors, starts, stops)
    ]
    lines = reduce(Zip, lines)
    spec = Fly(ConstantDuration(dwell_time, lines))
    # Prepare metadata
    md_args = tuple(zip([repr(m) for m in motors], starts, stops))
    md_args = tuple(obj for m, start, stop in md_args for obj in [m, start, stop])
    md_ = {
        "plan_name": "fly_scan",
        "motors": [motor.name for motor in motors],
        "detectors": [det.name for det in detectors],
        "scanspec": repr(spec),
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "*args": md_args,
            "num": num,
            "dwell_time": dwell_time,
            "trigger": str(trigger),
            "flyer_controllers": [repr(output) for output in flyer_controllers],
        },
    }
    md_.update(md)
    # Do the actual flying
    segment_plan = fly_segment(
        detectors=detectors,
        motors=motors,
        spec=spec,
        trigger_info=trigger_info,
        flyer_controllers=flyer_controllers,
    )
    segment_plan = run_wrapper(segment_plan, md=md_)
    segment_plan = stage_wrapper(segment_plan, [*detectors, *motors])
    yield from segment_plan


def _is_snaked(axis, snake_axes) -> bool:
    if isinstance(snake_axes, abc.Iterable):
        return axis in snake_axes
    else:
        return snake_axes


def _grid_scan_spec(*args, snake_axes: Iterable | bool, dwell_time: float) -> Spec:
    """Build the scan specification for a fly grid scan.

    Arguments should be a subset of those used in `grid_fly_scan`.

    """
    # Create the fly scan part of the spec
    *step_args, flyer, fly_start, fly_stop, fly_num = args
    fly_line = Line(flyer, fly_start, fly_stop, fly_num)
    if _is_snaked(flyer, snake_axes):
        fly_line = ~fly_line
    fly_line = Fly(ConstantDuration(dwell_time, fly_line))
    # Build the step-scan parts of the spec
    step = 4
    step_chunks = [step_args[n : n + step] for n in range(0, len(step_args), step)]
    step_lines = [
        Line(axis, start, stop, step) for axis, start, stop, step in step_chunks
    ]
    # Apply snaking, but not to the slowest axis
    step_lines = [
        step_lines[0],
        *[
            ~line if _is_snaked(line.axes, snake_axes) else line
            for line in step_lines[1:]
        ],
    ]
    # Apply snaking
    specs = [*step_lines, fly_line]
    # Combine the specs into a grid
    grid_spec = reduce(operator.mul, specs)
    return grid_spec


def grid_fly_scan(
    detectors: Sequence[Flyable],
    *args,
    dwell_time: float,
    trigger: DetectorTrigger = DetectorTrigger.INTERNAL,
    flyer_controllers: Sequence[Preparable] = [],
    snake_axes: Iterable | bool = False,
    md: Mapping = {},
):
    """Scan over a mesh with one of the axes collecting without stopping.

    Parameters
    ----------
    detectors
      list of 'readable' objects
    *args
      patterned like::

        motor1, start1, stop1, num1,
        motor2, start2, stop2, num2,
        ...
        flyer, flyer_start, flyer_stop, flyer_num

      The first motor is the "slowest", the outer loop. The last
      motor should be flyable.
    dwell_time
      How long, in seconds, for each measurement point.
    trigger
      The trigger mode to use for flying.
    flyer_controllers
      If provided, these devices (e.g. delay generator outputs) will
      be used to coordinate hardware triggering of detectors.
    snake_axes
      which axes should be snaked, either ``False`` (do not snake any axes),
      ``True`` (snake all axes) or a list of axes to snake. "Snaking" an axis
      is defined as following snake-like, winding trajectory instead of a
      simple left-to-right trajectory. The elements of the list are motors
      that are listed in `args`. The list must not contain the slowest
      (first) motor, since it can't be snaked.
    md: dict, optional
      metadata

    Yields
    ------
    msg
      'stage', 'open_run', 'mv', 'kickoff', 'wait', 'complete, 'wait',
      'collect', 'close_run', 'stage' messages.

    """
    # Build the scan specification for flying
    spec = _grid_scan_spec(*args, snake_axes=snake_axes, dwell_time=dwell_time)
    frames = spec.calculate()
    *step_frames, fly_frame = frames
    step_path = Path(step_frames)
    step_motors = [axis for frame in step_frames for axis in frame.axes()]
    fly_motors = fly_frame.axes()
    # Figure out how to trigger the detector (once per line)
    num_fly_points = args[-1]
    # For now, the aerotech is producing shorter segments than expected
    trigger_info = TriggerInfo(
        number_of_events=num_fly_points,
        livetime=dwell_time * 0.85,
        deadtime=dwell_time * 0.15,
        trigger=trigger,
    )

    # Set up plan-specific metadata
    extents: tuple[dict[str, tuple[float, float]], ...] = tuple(
        {
            axis.name: (float(np.min(points)), float(np.max(points)))
            for axis, points in frame.midpoints.items()
        }
        for frame in frames
    )
    args_for_md = [repr(arg) if isinstance(arg, HasName) else arg for arg in args]
    snake_repr = (
        [repr(arg) for arg in snake_axes]
        if isinstance(snake_axes, Iterable)
        else snake_axes
    )
    num_intervals = np.prod([len(frame) for frame in frames[:-1]]) * (
        len(frames[-1]) - 1
    )
    md_ = {
        "shape": tuple(len(frame) for frame in frames),
        "extents": extents,
        "scanspec": repr(spec),
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "args": args_for_md,
            "dwell_time": dwell_time,
            "trigger": str(trigger),
            "flyer_controllers": [repr(ctrlr) for ctrlr in flyer_controllers],
            "snake_axes": snake_repr,
            "md": md,
        },
        "plan_name": "grid_fly_scan",
        "num_points": int(np.prod([len(frame) for frame in frames])),
        "num_intervals": int(num_intervals),
        "plan_pattern": "outer_product",
        "motors": tuple(axis.name for axis in spec.axes()),
        "snaking": tuple(
            isinstance(dimension, SnakedDimension) for dimension in frames
        ),
        "hints": {
            "gridding": "rectilinear",
            "dimensions": [(m.hints["fields"], "primary") for m in spec.axes()],
        },
    }
    md_.update(md)

    @stage_decorator([*detectors, *step_motors, *fly_motors, *flyer_controllers])
    @run_decorator(md=md_)
    def inner_loop():
        while len(step_path) > 0:
            loop_iteration = step_path.index
            # Move the step-scanned motors to the next position
            next_point = step_path.consume(1)
            mv_args = [
                (motor, midpoints[0])
                for motor, midpoints in next_point.midpoints.items()
            ]
            mv_args = [arg for args in mv_args for arg in args]  # Flatten the list
            yield from bps.mv(*mv_args)
            # Execute the fly segment
            for motor in step_motors:
                yield from bps.monitor(motor, name=motor.name)
            yield from fly_segment(
                detectors=detectors,
                motors=fly_motors,
                spec=spec,
                flyer_controllers=flyer_controllers,
                start=loop_iteration * num_fly_points,
                num=num_fly_points,
                trigger_info=trigger_info,
            )
            for motor in step_motors:
                yield from bps.unmonitor(motor)

    yield from inner_loop()


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
