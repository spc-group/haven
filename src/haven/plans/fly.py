from bluesky import plan_stubs as bps

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
    for flyer in flyers:
        yield from bps.collect(flyer)
    yield from bps.close_run()
    return uid
