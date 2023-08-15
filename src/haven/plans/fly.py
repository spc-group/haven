from collections import OrderedDict, abc
from functools import partial

import numpy as np
from bluesky import plans as bp, plan_stubs as bps, plan_patterns
from ophyd import Device
from ophyd.flyers import FlyerInterface
from ophyd.status import StatusBase


def fly_line_scan(detectors, flyer, start, stop, num, extra_signals=()):
    """A plan stub for fly-scanning a single trajectory."""
    # Calculate parameters for the fly-scan
    step_size = abs(start - stop) / (num - 1)
    yield from bps.mv(flyer.start_position, start)
    yield from bps.mv(flyer.end_position, stop)
    yield from bps.mv(flyer.step_size, step_size)
    # Perform the fly scan
    flyers = [flyer, *detectors]
    for flyer in flyers:
        yield from bps.kickoff(flyer, wait=True)
    for flyer in flyers:
        yield from bps.complete(flyer, wait=True)
    # Collect the data after flying
    collector = FlyerCollector(flyers=flyers, name="flyer_collector", extra_signals=extra_signals)
    yield from bps.collect(collector)


def fly_scan(detectors, flyer, start: float, stop: float, num: int, md: dict = None):
    """Do a fly scan with a 'flyer' motor and some 'flyer' detectors.

    Parameters
    ----------
    detectors : list
        list of 'readable' objects that support the flyer interface
    flyer
      The thing going to get moved.
    start
      The center of the first pixel in *flyer*.
    stop
      The center of the last measurement in *flyer*.
    num
      Number of measurements to take.
    md : dict, optional
      metadata

    Yields
    ------
    msg : Msg
        'kickoff', 'wait', 'complete, 'wait', 'collect' messages

    """
    uid = yield from bps.open_run(md)
    yield from fly_line_scan(detectors, flyer, start, stop, num)
    yield from bps.close_run()
    return uid


def grid_fly_scan(detectors, *args, snake_axes: bool = None, md=None):
    """Scan over a mesh with one of the axes collects without stopping.

    Parameters
    ----------
    detectors: list
        list of 'readable' objects
    ``*args``
        patterned like (``motor1, start1, stop1, num1,``
                        ``motor2, start2, stop2, num2,``
                        ``motor3, start3, stop3, num3,`` ...
                        ``motorN, startN, stopN, numN``)
        The first motor is the "slowest", the outer loop. The last
        motor should be flyable. For all motors except the first
        motor, there is a "snake" argument: a boolean indicating
        whether to following snake-like, winding trajectory or a
        simple left-to-right trajectory.
    snake_axes: boolean or iterable, optional
        which axes should be snaked, either ``False`` (do not snake any axes),
        ``True`` (snake all axes) or a list of axes to snake. "Snaking" an axis
        is defined as following snake-like, winding trajectory instead of a
        simple left-to-right trajectory. The elements of the list are motors
        that are listed in `args`. The list must not contain the slowest
        (first) motor, since it can't be snaked.
    md: dict, optional
        metadata

    """
    # Extract the step-scan vs fly-scan arguments
    *step_args, flyer, fly_start, fly_stop, fly_num = args
    # Handle giving snaked axes as a list
    arg_chunks = list(plan_patterns.chunk_outer_product_args(step_args))
    num_steppers = len(arg_chunks)
    motors = [m[0] for m in arg_chunks]
    if isinstance(snake_axes, abc.Iterable) and not isinstance(snake_axes, str):
        snake_steppers = snake_axes.copy()
        try:
            snake_steppers.remove(flyer)
        except ValueError:
            snake_flyer = False
        else:
            snake_flyer = True
    else:
        snake_steppers = snake_axes
        snake_flyer = snake_axes
    # Set up the plan
    per_step = Snaker(
        snake_axes=snake_flyer,
        flyer=flyer,
        start=fly_start,
        stop=fly_stop,
        num=fly_num,
        extra_signals=motors,
    )
    uid = yield from bp.grid_scan(
        detectors, *step_args, snake_axes=snake_steppers, per_step=per_step
    )
    return uid


class Snaker:
    """Executes 1-D fly line scans in a snaking motion.

    Each call of the snaker executes the same fly-scan, but supports
    alternating scan directions to save time.

    This callable's signature is compatible with bluesky's
    ``per_step`` option for scans, so instead of just reading a
    detector, a whole fly-scan is performed."

    """

    reverse: bool = False

    def __init__(self, snake_axes, flyer, start, stop, num, extra_signals):
        self.snake_axes = snake_axes
        self.flyer = flyer
        self.start = start
        self.stop = stop
        self.num = num
        self.extra_signals = extra_signals

    def __call__(self, detectors, step, pos_cache):
        # Move the step-scanning motors to the correct position
        yield from bps.move_per_step(step, pos_cache)
        # Determine line scans range based on snaking
        start, stop = (self.start, self.stop)
        if self.reverse:
            start, stop = stop, start
        self.reverse = not self.reverse
        # Launch the fly scan
        yield from fly_line_scan(
            detectors,
            flyer=self.flyer,
            start=start,
            stop=stop,
            num=self.num,
            extra_signals=step.keys(),
        )


class FlyerCollector(FlyerInterface, Device):
    stream_name: str
    flyers: list

    def __init__(
        self, flyers, stream_name: str = "primary", extra_signals=(), *args, **kwargs
    ):
        self.flyers = flyers
        self.stream_name = stream_name
        self.extra_signals = extra_signals
        super().__init__(*args, **kwargs)

    def kickoff(self):
        return StatusBase(success=True)

    def complete(self):
        return StatusBase(success=True)

    def collect(self):
        collections = [iter(flyer.collect()) for flyer in self.flyers]
        while True:
            event = {
                "data": {},
                "timestamps": {},
            }
            try:
                for coll in collections:
                    datum = next(coll)
                    event["data"].update(datum["data"])
                    event["timestamps"].update(datum["timestamps"])
            except StopIteration:
                break
            # Use the median time stamps for the overall event time
            timestamps = []
            for ts in event["timestamps"].values():
                timestamps.extend(np.asarray(ts).flatten())
            event["time"] = np.median(timestamps)
            # Add extra non-flying signals (not inc. in event time)
            for signal in self.extra_signals:
                for signal_name, reading in signal.read().items():
                    event["data"][signal_name] = reading["value"]
                    event["timestamps"][signal_name] = reading["timestamp"]
            yield event

    def describe_collect(self):
        desc = OrderedDict()
        for flyer in self.flyers:
            for stream, this_desc in flyer.describe_collect().items():
                desc.update(this_desc)
        # Add extra signals, e.g. slow motor during a grid fly scan
        for signal in self.extra_signals:
            desc.update(signal.describe())
        return {self.stream_name: desc}
