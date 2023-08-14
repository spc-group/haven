from collections import OrderedDict

import numpy as np
from bluesky import plan_stubs as bps
from ophyd import Device
from ophyd.flyers import FlyerInterface
from ophyd.status import StatusBase


def fly_scan(detectors, flyer, start, stop, num, dwell_time, md=None):
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
    dwell_time
      How long should the flyer take to traverse each measurement, in
      seconds.
    md : dict, optional
      metadata

    Yields
    ------
    msg : Msg
        'kickoff', 'wait', 'complete, 'wait', 'collect' messages

    """
    uid = yield from bps.open_run(md)
    # Set fly-scan parameters on the motor
    step_size = abs(start - stop) / (num - 1)
    yield from bps.mv(flyer.start_position, start)
    yield from bps.mv(flyer.end_position, stop)
    yield from bps.mv(flyer.step_size, step_size)
    yield from bps.mv(flyer.dwell_time, dwell_time)
    # Perform the fly scan
    flyers = [flyer, *detectors]
    for flyer in flyers:
        yield from bps.kickoff(flyer, wait=True)
    for flyer in flyers:
        yield from bps.complete(flyer, wait=True)
    # Collect the data after flying
    collector = FlyerCollector(flyers=flyers, name="flyer_collector")
    yield from bps.collect(collector)
    yield from bps.close_run()
    return uid


class FlyerCollector(FlyerInterface, Device):
    stream_name: str
    flyers: list

    def __init__(self, flyers, stream_name: str = "primary", *args, **kwargs):
        self.flyers = flyers
        self.stream_name = stream_name
        super().__init__(*args, **kwargs)

    def kickoff(self):
        return StatusBase(success=True)

    def complete(self):
        return StatusBase(success=True)

    def kickoff(self):
        pass

    def complete(self):
        pass

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
            for ts in event['timestamps'].values():
                timestamps.extend(np.asarray(ts).flatten())
            print(timestamps)
            event['time'] = np.median(timestamps)
            yield event

    def describe_collect(self):
        desc = OrderedDict()
        for flyer in self.flyers:
            for stream, this_desc in flyer.describe_collect().items():
                desc.update(this_desc)
        return {self.stream_name: desc}
