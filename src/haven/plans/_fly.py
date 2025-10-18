import operator
import uuid
from collections import OrderedDict, abc
from collections.abc import Generator, Iterable, Mapping, MutableMapping, Sequence
from functools import reduce
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
    run_wrapper,
    stage_decorator,
    stage_wrapper,
    stub_wrapper,
)
from bluesky.protocols import Collectable, Flyable, HasName, Preparable
from bluesky.utils import Msg, single_gen
from ophyd_async.core import DetectorTrigger, Device, TriggerInfo
from ophyd_async.epics.motor import FlyMotorInfo as BaseFlyMotorInfo
from pydantic import Field
from scanspec.core import Path, SnakedDimension
from scanspec.specs import ConstantDuration, Fly, Line, Spec, Zip

from haven._iconfig import load_config
from haven.devices.delay import DG645DelayOutput

__all__ = ["fly_scan", "grid_fly_scan"]


class FlyMotorInfo(BaseFlyMotorInfo):
    point_count: int = Field(frozen=True, gt=1)
    """How many points will be will be measured during the fly scan. This
    will be one less than the number of trigger."""


def reset_flyers_wrapper(
    plan: Generator[Msg, Any, Any], devices: Sequence[Flyable] | None = None
):
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
    initial_positions: MutableMapping[Flyable, float] = OrderedDict()
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


def unmonitor_motors(motors):
    for motor in motors:
        sig = getattr(motor, "user_readback", motor)
        yield from bps.unmonitor(sig)


def monitor_motors(motors):
    for motor in motors:
        sig = getattr(motor, "user_readback", motor)
        yield from bps.monitor(sig, name=motor.name)


def fly_line_scan(
    detectors: Sequence, *args, trigger_info=None, delay_outputs=[]
) -> Generator[Msg, Any, None]:
    """A plan stub for fly-scanning a single trajectory.

    Parameters
    ==========
    detectors
      Will be kicked off before the motors begin to move.
    *args
      A motor and FlyMotorInfo() object for each axis:

      .. code-block:: python

         motor1, fly_info1,
         motor2, fly_info2,
         ...,
         motorN, trigger_infoN,

      Motors can be any ‘flyable’ object.

    """
    trigger_infos = yield from prepare_detectors(
        detectors=detectors,
        trigger_info=trigger_info,
        delay_outputs=delay_outputs,
        wait=True,
    )
    num_outputs = 0  # for now they're all just different streams
    yield from declare_streams(detectors[:num_outputs], detectors[num_outputs:])
    # Set up motors in their taxi position
    motors = args[0::2]
    motor_infos = args[1::2]
    prepare_group = uuid.uuid4()
    for obj, motor_info in zip(motors, motor_infos):
        yield from bps.prepare(obj, motor_info, wait=False, group=prepare_group)
    yield from bps.wait(group=prepare_group)
    # Kickoff the detectors
    yield from bps.kickoff_all(*detectors, wait=True)
    # Perform the fly scan
    yield from monitor_motors(motors)
    kickoff_group = uuid.uuid4()
    for motor in motors:
        yield from bps.kickoff(motor, wait=False, group=kickoff_group)
    yield from bps.wait(group=kickoff_group)
    # Wait for all the flyers to be done
    motor_complete_group = uuid.uuid4()
    for m in motors:
        yield from bps.complete(m, wait=False, group=motor_complete_group)
    yield from bps.wait(group=(motor_complete_group))
    yield from unmonitor_motors(motors)
    # Stop the detectors
    yield from bps.complete_all(*detectors, wait=True)
    # Collect measured data so far
    collectables = [
        detector for detector in detectors if isinstance(detector, Collectable)
    ]
    for detector in collectables:
        yield from bps.collect(detector)


def fly_line_scan_old(
    detectors: Sequence,
    *args,
) -> Generator[Msg, Any, None]:
    """A plan stub for fly-scanning a single trajectory.

    Parameters
    ==========
    detectors
      Will be kicked off before the motors begin to move.
    *args
      A motor and FlyMotorInfo() object for each axis:

      .. code-block:: python

         motor1, fly_info1,
         motor2, fly_info2,
         ...,
         motorN, trigger_infoN,

      Motors can be any ‘flyable’ object.

    """
    # Set up motors in their taxi position
    motors = args[0::2]
    motor_infos = args[1::2]
    prepare_group = uuid.uuid4()
    for obj, motor_info in zip(motors, motor_infos):
        yield from bps.prepare(obj, motor_info, wait=False, group=prepare_group)
    yield from bps.wait(group=prepare_group)
    # Kickoff the detectors
    yield from bps.kickoff_all(*detectors, wait=True)
    # Perform the fly scan
    yield from monitor_motors(motors)
    kickoff_group = uuid.uuid4()
    for motor in motors:
        yield from bps.kickoff(motor, wait=False, group=kickoff_group)
    yield from bps.wait(group=kickoff_group)
    # Wait for all the flyers to be done
    motor_complete_group = uuid.uuid4()
    for m in motors:
        yield from bps.complete(m, wait=False, group=motor_complete_group)
    yield from bps.wait(group=(motor_complete_group))


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


def fly_scan(
    detectors: Sequence[Flyable],
    *args,
    num: int,
    dwell_time: float,
    trigger: DetectorTrigger = DetectorTrigger.INTERNAL,
    delay_outputs: Sequence[Preparable] = [],
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
    md_args = tuple(zip([repr(m) for m in motors], starts, stops))
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
            "trigger": str(trigger),
            "delay_outputs": [repr(output) for output in delay_outputs],
        },
    }
    md_.update(md)
    # Create the plan for moving over a single line
    delays = set([output.parent for output in delay_outputs])
    if load_config().feature_flag("grid_fly_scan_by_line"):
        line_scan = fly_line_scan(
            [*delays, *delay_outputs, *detectors],
            *motor_args,
            trigger_info=trigger_info,
        )
    else:
        line_scan = fly_line_scan_old(
            [*delays, *delay_outputs, *detectors],
            *motor_args,
        )

    # Wrapper for making it a proper run
    @stage_decorator([*detectors, *motors])
    @run_decorator(md=md_)
    def fly_inner():
        # Start the detectors
        if not load_config().feature_flag("grid_fly_scan_by_line"):
            yield from prepare_detectors(
                detectors=detectors,
                trigger_info=trigger_info,
                delay_outputs=delay_outputs,
                wait=True,
            )
            num_outputs = len(delay_outputs)
            num_outputs = 0  # for now they're all just different streams
            yield from declare_streams(detectors[:num_outputs], detectors[num_outputs:])
            # Execute the fly scan and Keep track of the motor positions
            yield from monitor_motors(motors)
            yield from finalize_wrapper(line_scan, unmonitor_motors(motors))
            # Stop detectors
            if not load_config().feature_flag("grid_fly_scan_by_line"):
                yield from bps.complete_all(*detectors, wait=True)
                for detector in detectors:
                    yield from bps.collect(detector)
        else:
            yield from line_scan

    yield from fly_inner()


def grid_fly_scan(
    detectors: Sequence[Flyable],
    *args,
    dwell_time: float,
    trigger: DetectorTrigger = DetectorTrigger.INTERNAL,
    delay_outputs: Sequence[Preparable] = [],
    snake_axes: Iterable | bool | None = False,
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
    snake_steppers: Iterable | bool | None
    if isinstance(snake_axes, abc.Iterable):
        snake_steppers = [ax for ax in snake_axes if ax is not flyer]
        snake_flyer = flyer in snake_axes
        # Save for metadata processing
        snaking = [
            (motor in snake_steppers) for motor, start, stop, num, snake in step_chunks
        ]
        snaking = [False, *snaking[1:], snake_flyer]
    else:
        snake_steppers = snake_axes
        snake_flyer = bool(snake_axes)
        snaking = [False, *[bool(snake_axes) for _ in step_chunks[1:]], snake_flyer]
    # Decide how to trigger the detectors
    step_num = np.prod([chunk[3] for chunk in step_chunks])
    trigger_info = TriggerInfo(
        number_of_events=[fly_num] * step_num,
        livetime=dwell_time * 0.85,
        deadtime=dwell_time * 0.15,
        trigger=trigger,
    )
    # Prepare metadata
    chunk_args = list(plan_patterns.chunk_outer_product_args(args))
    md_args = []
    motor_names = []
    for i, (motor, start, stop, num, snake) in enumerate(chunk_args):
        md_args.extend([repr(motor), start, stop, num])
        motor_names.append(motor.name)
    num_points = np.prod([num for motor, start, stop, num, snake in chunk_args])
    snake_repr: Iterable | bool | None
    try:
        snake_repr = [repr(ax) for ax in snake_axes]  # type: ignore
    except TypeError:
        snake_repr = snake_axes
    pattern_args = []
    for idx, obj in enumerate(args):
        if not (idx % 4):
            obj = repr(obj)
        pattern_args.append(obj)
    md_ = {
        "shape": tuple(num for motor, start, stop, num, snake in chunk_args),
        "extents": tuple(
            [start, stop] for motor, start, stop, num, snake in chunk_args
        ),
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "args": md_args,
            "dwell_time": dwell_time,
            "trigger": str(trigger),
            "delay_outputs": [repr(output) for output in delay_outputs],
            "snake_axes": snake_repr,
        },
        "plan_name": "grid_fly_scan",
        "num_points": num_points,
        "num_intervals": num_points - 1,
        "plan_pattern": "outer_product",
        "plan_pattern_args": {
            "args": pattern_args,
        },
        "plan_pattern_module": "bluesky.plan_patterns",
        "motors": tuple(motor_names),
        "snaking": snaking,
        "hints": {
            "gridding": "rectilinear",
            "dimensions": [(m.hints["fields"], "primary") for m in all_motors],
        },
    }
    md_.update(md)

    # Wrapper for making it a proper run
    @stage_decorator([*detectors, *motors])
    @run_decorator(md=md_)
    def fly_inner():
        # Start the detectors (moved to the snaker until we can get the gate correct)
        if load_config().feature_flag("grid_fly_scan_by_line"):
            delays = set([output.parent for output in delay_outputs])
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
                trigger_info=trigger_info,
            )
            grid_scan = stub_wrapper(
                bp.grid_scan(
                    detectors,
                    *step_args,
                    snake_axes=snake_steppers,
                    per_step=per_step,
                    md=md_,
                )
            )
            # Execute the fly scan and Keep track of the motor positions
            result = yield from grid_scan
            return result

        else:
            trigger_infos = yield from prepare_detectors(
                detectors=detectors,
                trigger_info=trigger_info,
                delay_outputs=delay_outputs,
                wait=True,
            )
            # num_outputs = len(delay_outputs)
            num_outputs = 0  # for now they're all just different streams
            yield from declare_streams(detectors[:num_outputs], detectors[num_outputs:])
            # Do the true original plan
            delays = set([output.parent for output in delay_outputs])
            per_step = Snaker(
                snake_axes=snake_flyer,
                flyer=flyer,
                start=fly_start,
                stop=fly_stop,
                num=fly_num,
                dwell_time=dwell_time,
                trigger=trigger,
                delay_outputs=[*delays, *delay_outputs],
                extra_signals=motors,
                trigger_infos=trigger_infos,
            )
            grid_scan = stub_wrapper(
                bp.grid_scan(
                    detectors,
                    *step_args,
                    snake_axes=snake_steppers,
                    per_step=per_step,
                    md=md_,
                )
            )
            # Execute the fly scan and Keep track of the motor positions
            yield from monitor_motors(all_motors)
            result = yield from finalize_wrapper(
                grid_scan, unmonitor_motors(all_motors)
            )
            # Tear down the scan
            yield from bps.complete_all(*detectors, wait=True)
            for detector in detectors:
                yield from bps.collect(detector)
            return result

    return (yield from fly_inner())


def prepare_detectors(
    detectors: Sequence[Device],
    trigger_info: TriggerInfo,
    delay_outputs: Sequence[DG645DelayOutput] = [],
    group: Hashable | None = None,
    wait: bool = False,
) -> Generator[Msg, Any, list[TriggerInfo]]:
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
        return trigger_infos
    delay_generators = {output.parent for output in delay_outputs}
    for generator in delay_generators:
        yield from bps.prepare(generator, trigger_info)
    # Prepare the delay generator outputs
    trigger_output_infos: dict[Device, TriggerInfo] = {}
    for output, tinfo in zip(delay_outputs, trigger_infos):
        trigger_output_infos.setdefault(output, []).append(tinfo)
    for output, tinfos in trigger_output_infos.items():
        # Make sure we're only setting each output once, and consistently
        if not all([tinfo == tinfos[0] for tinfo in tinfos]):
            raise RuntimeError(
                "Detectors cannot agree on trigger info for delay output "
                f"{output.name}: {tinfos}"
            )
        yield from bps.prepare(output, tinfos[0], wait=wait, group=group)
    if wait:
        yield from bps.wait(group=group)
    return trigger_infos


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
        trigger_infos=[],
        trigger_info=None,
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
        self.trigger_infos = trigger_infos
        self.trigger_info = trigger_info

    def __call__(self, detectors, step, pos_cache):
        # Move the step-scanning motors to the correct position
        yield from bps.move_per_step(step, pos_cache)
        # Determine line scan range based on snaking
        start, stop = (self.start, self.stop)
        if self.reverse and self.snake_axes:
            start, stop = stop, start
        self.reverse = not self.reverse
        # Launch the fly scan
        fly_motor_info = FlyMotorInfo(
            start_position=start,
            end_position=stop,
            time_for_move=self.dwell_time * self.num,
            point_count=self.num,
        )
        if load_config().feature_flag("grid_fly_scan_by_line"):
            yield from fly_line_scan(
                detectors,
                self.flyer,
                fly_motor_info,
                delay_outputs=self.delay_outputs,
                trigger_info=self.trigger_info,
            )
        else:
            # Only some detectors (edge triggers) need to fly, gated
            # detectors should be flown from the calling plan and will
            # continue flying for the next step.
            to_fly = [
                detector
                for trig_info, detector in zip(self.trigger_infos, detectors)
                if trig_info.trigger == DetectorTrigger.EDGE_TRIGGER
            ]
            yield from fly_line_scan_old(
                to_fly + self.delay_outputs, self.flyer, fly_motor_info
            )
            # Collect data from the detectors. Only detectors using
            # triggers need to complete here, gates can just keep going.
            #   This currently doesn't work because we can't control the
            #   pulses properly. It leaves an extra frame at the end of
            #   every gated signal.
            yield from bps.complete_all(*to_fly, wait=True)
            for detector in detectors:
                yield from bps.collect(detector)


# New style from here down
# ========================


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


def fly_scan_with_spec(
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
    # Prepare metadata
    md_args = tuple(zip([repr(m) for m in motors], starts, stops))
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
            "trigger": str(trigger),
            "flyer_controllers": [repr(output) for output in flyer_controllers],
        },
    }
    md_.update(md)
    # Do the actual flying
    lines = [
        Line(motor, start, stop, num)
        for (motor, start, stop) in zip(motors, starts, stops)
    ]
    lines = reduce(Zip, lines)
    spec = Fly(ConstantDuration(dwell_time, lines))
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


def grid_fly_scan_with_spec(
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
