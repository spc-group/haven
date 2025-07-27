import uuid
from collections import OrderedDict, abc
from collections.abc import Generator, Mapping, Sequence
from typing import Any, Hashable

import numpy as np
from bluesky import plan_patterns
from bluesky import plan_stubs as bps
from bluesky import plans as bp
from bluesky.preprocessors import (
    __read_and_stash_a_motor,
    _normalize_devices,
    finalize_wrapper,
    pchain,
    plan_mutator,
    run_decorator,
    stage_decorator,
    stub_wrapper,
)
from bluesky.protocols import Collectable
from bluesky.utils import Msg, single_gen
from ophyd import Device
from ophyd.flyers import FlyerInterface
from ophyd.status import StatusBase
from ophyd_async.core import DetectorTrigger, TriggerInfo
from ophyd_async.epics.motor import FlyMotorInfo as BaseFlyMotorInfo
from pydantic import Field

from haven.devices.delay import DG645DelayOutput

__all__ = ["fly_scan", "grid_fly_scan"]


class FlyMotorInfo(BaseFlyMotorInfo):
    point_count: int = Field(frozen=True, gt=1)
    """How many points will be will be measured during the fly scan. This
    will be one less than the number of trigger."""


def reset_flyers_wrapper(plan, devices=None):
    """Return flyer devices to their initial positions and velocities
    prior to being prepared for flying.

    Parameters
    ----------
    plan : iterable or iterator
        a generator, list, or similar containing `Msg` objects
    devices : collection or None, optional
        If default (None), apply to all devices that are prepared by the plan.

    Yields
    ------
    msg : Msg
        messages from plan with 'read' and finally 'set' messages inserted

    """
    initial_positions = OrderedDict()
    if devices is not None:
        devices, coupled_parents = _normalize_devices(devices)
    else:
        coupled_parents = set()

    def insert_reads(msg):
        eligible = devices is None or msg.obj in devices
        seen = msg.obj in initial_positions
        if (msg.command == "prepare") and eligible and not seen:
            # Stash flyer position
            plan_bits = [
                __read_and_stash_a_motor(msg.obj, initial_positions, coupled_parents)
            ]
            # Stash flyer velocity
            if hasattr(msg.obj, "velocity"):
                plan_bits.append(
                    __read_and_stash_a_motor(
                        msg.obj.velocity, initial_positions, coupled_parents
                    )
                )
            return (pchain(*plan_bits, single_gen(msg)), None)
        else:
            return None, None

    def reset():
        blk_grp = f"reset-{str(uuid.uuid4())[:6]}"
        for k, v in initial_positions.items():
            if k.parent in coupled_parents:
                continue
            yield Msg("set", k, v, group=blk_grp)
        yield Msg("wait", None, group=blk_grp)

    return (yield from finalize_wrapper(plan_mutator(plan, insert_reads), reset()))


def fly_line_scan(*args) -> Generator[Msg, Any, None]:
    """A plan stub for fly-scanning a single trajectory.

    Parameters
    ==========
    *args
      A motor and FlyMotorInfo() object for each axis:

      .. code-block:: python

         motor1, fly_info1,
         motor2, fly_info2,
         ...,
         motorN, trigger_infoN,

      Motors can be any ‘flyable’ object.

    """
    motors = args[0::2]
    motor_infos = args[1::2]
    # Set up motors in their taxi position
    prepare_group = uuid.uuid4()
    for obj, motor_info in zip(motors, motor_infos):
        yield from bps.prepare(obj, motor_info, wait=False, group=prepare_group)
    yield from bps.wait(group=prepare_group)
    # Monitor the motors during their move
    for motor in motors:
        sig = motor.user_readback
        yield from bps.monitor(sig, name=sig.name)
    # Perform the fly scan
    kickoff_group = uuid.uuid4()
    for motor in motors:
        yield from bps.kickoff(motor, wait=False, group=kickoff_group)
    yield from bps.wait(group=kickoff_group)
    # Wait for all the flyers to be done
    motor_complete_group = uuid.uuid4()
    for m in motors:
        yield from bps.complete(m, wait=False, group=motor_complete_group)
    yield from bps.wait(group=(motor_complete_group))
    # Stop monitoring motors
    for motor in motors:
        sig = motor.user_readback
        yield from bps.unmonitor(sig)


def fly_scan(
    detectors: Sequence[FlyerInterface],
    *args,
    num: int,
    dwell_time: float,
    trigger: DetectorTrigger = DetectorTrigger.INTERNAL,
    delay_outputs: Sequence[DG645DelayOutput] = [],
    md: Mapping = {},
):
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
    # Prepare the motor info
    motors = args[0::3]
    starts = args[1::3]
    stops = args[2::3]
    motor_args = []
    for motor, start, stop in zip(motors, starts, stops):
        motor_info = FlyMotorInfo(
            start_position=start,
            end_position=stop,
            time_for_move=dwell_time * num,
            point_count=num,
        )
        motor_args.extend([motor, motor_info])
    # Prepare detector triggering info
    trigger_info = TriggerInfo(
        number_of_events=num,
        livetime=dwell_time * 0.85,
        deadtime=dwell_time * 0.15,
        trigger=trigger,
    )
    # Prepare metadata
    md_args = zip([repr(m) for m in motors], starts, stops)
    md_args = tuple(obj for m, start, stop in md_args for obj in [m, start, stop])
    md_ = {
        "plan_name": "fly_scan",
        "motors": [motor.name for motor in motors],
        "detectors": [det.name for det in detectors],
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "*args": md_args,
            "num": num,
            "dwell_time": dwell_time,
            "delay_outputs": [repr(output) for output in delay_outputs],
        },
    }
    md_.update(md)
    # Create the plan for moving over a single line
    line_scan = fly_line_scan(
        *motor_args,
    )
    # Wrapper for making it a proper run
    @stage_decorator([*detectors, *motors])
    @run_decorator(md=md_)
    def fly_inner():
        # Set up detector streams
        n_outputs = len(delay_outputs)
        triggered_detectors = detectors[:n_outputs]
        internal_detectors = detectors[n_outputs:]
        yield from bps.declare_stream(*triggered_detectors, name="primary")
        for detector in internal_detectors:
            yield from bps.declare_stream(detector, name=detector.name)
        # Start the detectors
        prepare_group = uuid.uuid4()
        yield from prepare_detectors(
            detectors=detectors,
            trigger_info=trigger_info,
            delay_outputs=delay_outputs,
            wait=True,
        )
        yield from bps.kickoff_all(*detectors, wait=True)
        # Fly the motors
        yield from line_scan
        # Stop detectors
        yield from bps.complete_all(*detectors, wait=True)
        for detector in detectors:
            yield from bps.collect(detector)

    yield from fly_inner()


def grid_fly_scan(
    detectors: Sequence[FlyerInterface],
    *args,
    dwell_time: float,
    trigger: DetectorTrigger = DetectorTrigger.INTERNAL,
    delay_outputs: Sequence[DG645DelayOutput] = [],
    snake_axes: bool | Sequence[Device] = False,
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
    delay_outputs
      If provided, these delay generator outputs will be used to
      coordinate hardware triggering of detectors.
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
    # Extract the step-scan vs fly-scan arguments
    *step_args, flyer, fly_start, fly_stop, fly_num = args
    # Handle giving snaked axes as a list
    step_chunks = list(plan_patterns.chunk_outer_product_args(step_args))
    num_steppers = len(step_chunks)
    motors = [m[0] for m in step_chunks]
    all_motors = [*motors, flyer]
    if isinstance(snake_axes, abc.Iterable) and not isinstance(snake_axes, str):
        snake_steppers = snake_axes.copy()
        try:
            snake_steppers.remove(flyer)
        except ValueError:
            snake_flyer = False
        else:
            snake_flyer = True
        # Save for metadata processing
        snaking = [
            (motor in snake_steppers) for motor, start, stop, num, snake in step_chunks
        ]
        snaking = (False, *snaking[1:], snake_flyer)
    else:
        snake_steppers = snake_axes
        snake_flyer = snake_axes
        snaking = [False, *[snake_axes for _ in step_chunks[1:]], snake_flyer]
    # Prepare metadata
    chunk_args = list(plan_patterns.chunk_outer_product_args(args))
    md_args = []
    motor_names = []
    for i, (motor, start, stop, num, snake) in enumerate(chunk_args):
        md_args.extend([repr(motor), start, stop, num])
        motor_names.append(motor.name)
    num_points = np.prod([num for motor, start, stop, num, snake in chunk_args])
    try:
        snake_repr = [repr(ax) for ax in snake_axes]
    except TypeError:
        snake_repr = snake_axes
    md_ = {
        "shape": tuple(num for motor, start, stop, num, snake in chunk_args),
        "extents": tuple(
            [start, stop] for motor, start, stop, num, snake in chunk_args
        ),
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "args": md_args,
            "dwell_time": dwell_time,
            "trigger": trigger,
            "delay_outputs": [repr(output) for output in delay_outputs],
            "snake_axes": snake_repr,
        },
        "plan_name": "grid_fly_scan",
        "num_points": num_points,
        "num_intervals": num_points - 1,
        "motors": tuple(motor_names),
        "snaking": snaking,
        "hints": {},
    }
    # Add metadata hints for plotting, etc
    md_["hints"].setdefault("gridding", "rectilinear")
    try:
        md_["hints"].setdefault(
            "dimensions", [(m.hints["fields"], "primary") for m in all_motors]
        )
    except (AttributeError, KeyError):
        ...
    md_.update(md)
    # Set up the plan
    per_step = Snaker(
        snake_axes=snake_flyer,
        flyer=flyer,
        start=fly_start,
        stop=fly_stop,
        num=fly_num,
        dwell_time=dwell_time,
        trigger=trigger,
        delay_outputs=delay_outputs,
        extra_signals=motors,
    )
    grid_scan = bp.grid_scan(
        detectors,
        *step_args,
        snake_axes=snake_steppers,
        per_step=per_step,
        md=md_,
    )
        # Wrapper for making it a proper run
    @stage_decorator([*detectors, *motors])
    @run_decorator(md=md_)
    def fly_inner():
        # Set up detector streams
        n_outputs = len(delay_outputs)
        triggered_detectors = detectors[:n_outputs]
        internal_detectors = detectors[n_outputs:]
        yield from bps.declare_stream(*triggered_detectors, name="primary")
        for detector in internal_detectors:
            yield from bps.declare_stream(detector, name=detector.name)
        # Do the true original plan
        return (yield from stub_wrapper(grid_scan))

    return (yield from fly_inner())


def prepare_detectors(
    detectors: Sequence[Device],
    trigger_info: TriggerInfo,
    delay_outputs: Sequence[DG645DelayOutput] = [],
    group: Hashable | None = None,
    wait: bool = False,
) -> Generator[Msg, Any, None]:
    """A Bluesky plan stub to prepare detectors for flying.

    A delay generator can be used to handle trigger mutation. Each
    detector in *detectors* will be asked to provide a validation
    trigger info that may be different than *trigger_info*.

    Parameters
    ==========
    detectors
      The detectors for which the DG645 will be configured.
    trigger_info
      The nominal trigger info for this scan.
    delay_outputs
      A sequence of DG645 delay generator output devices that will be
      configured for each detector.

    """
    trigger_infos: list[TriggerInfo] = []
    group = group or str(uuid.uuid4())
    # Prepare the detectors
    for detector in detectors:
        tinfo = getattr(detector, "validate_trigger_info", lambda x: x)(trigger_info)
        yield from bps.prepare(detector, tinfo, wait=wait, group=group)
        trigger_infos.append(tinfo)
    # Prepare the delay generator input
    if len(delay_outputs) == 0:
        return
    delay_generators = {output.parent for output in delay_outputs}
    for generator in delay_generators:
        yield from bps.prepare(generator, trigger_info)
    # Prepare the delay generator outputs
    trigger_output_infos = {}
    for output, tinfo in zip(delay_outputs, trigger_infos):
        trigger_output_infos.setdefault(output, []).append(tinfo)
    for output, tinfos in trigger_output_infos.items():
        # Make sure we're only setting each output once, and consistently
        if not all([tinfo == tinfos[0] for tinfo in tinfos]):
            raise RuntimeError(
                "Detectors cannot agree on trigger info for delay output "
                f"{output.name}: {tinfos}"
            )
        yield from bps.prepare(output, tinfos[0])
    if wait:
        yield from bps.wait(group=group)


class Snaker:
    """Executes 1-D fly line scans in a snaking motion.

    Each call of the snaker executes the same fly-scan, but supports
    alternating scan directions to save time.

    This callable's signature is compatible with bluesky's
    ``per_step`` option for scans, so instead of just reading a
    detector, a whole fly-scan is performed."

    """

    reverse: bool = False

    def __init__(
        self,
        snake_axes: bool,
        flyer: Device,
        start: float,
        stop: float,
        num: int,
        dwell_time: float,
        trigger: DetectorTrigger,
        delay_outputs: Sequence[Device],
        extra_signals,
    ):
        self.snake_axes = snake_axes
        self.flyer = flyer
        self.start = start
        self.stop = stop
        self.num = num
        self.dwell_time = dwell_time
        self.trigger = trigger
        self.delay_outputs = delay_outputs
        self.extra_signals = extra_signals

    def __call__(self, detectors, step, pos_cache):
        # Move the step-scanning motors to the correct position
        yield from bps.move_per_step(step, pos_cache)
        # Determine line scans range based on snaking
        start, stop = (self.start, self.stop)
        if self.reverse and self.snake_axes:
            start, stop = stop, start
        self.reverse = not self.reverse
        # Launch the fly scan
        yield from fly_line_scan(
            detectors,
            self.flyer,
            start,
            stop,
            dwell_time=self.dwell_time,
            trigger=self.trigger,
            delay_outputs=self.delay_outputs,
            num=self.num,
        )


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
