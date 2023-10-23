import time
import warnings
import logging

from bluesky.preprocessors import subs_decorator, subs_wrapper
from bluesky.callbacks import best_effort
from bluesky import plan_stubs as bps
from apstools.plans.alignment import lineup

from ..instrument.instrument_registry import registry
from ..preprocessors import shutter_suspend_decorator

log = logging.getLogger(__name__)


__all__ = ["align_motor", "align_pitch2"]


# @shutter_suspend_decorator()
def align_pitch2(
    distance=200, reverse=False, detector="I0", bec=None, feature="cen", md={}
):
    """Tune the monochromator 2nd crystal pitch motor.

    Find and set the position of maximum intensity in the ion chamber
    "I0". The scanning range is relative to the current motor
    position, and will go *distance* above and below it. For example,
    if the current position is 1000, ``distance=200`` will scan from
    800 to 1200.

    Parameters
    ==========
    bec
      A bluesky best effort callback for finding the peak position.
    distance
      Relative distance to scan in either direction.
    reverse
      Whether the scan goes low-to-high (False) or high-to-low (True).
    detector
      Which detector name to use.
    feature
      Which feature of the peak to use for alignment.
    md
      Extra metadata to pass into the run engine.

    """
    md_ = dict(plan_name="align_pitch2")
    md_.update(md)
    # Get motors
    pitch2 = registry.find(name="monochromator_pitch2")
    # Prepare and run the plan
    yield from align_motor(
        detector=detector,
        motor=pitch2,
        distance=distance,
        reverse=reverse,
        bec=bec,
        feature=feature,
        md=md_,
    )


@shutter_suspend_decorator()
def align_motor(
    detector, motor, distance=200, reverse=False, bec=None, feature="cen", md={}
):
    """Center the given motor using the beam intensity.

    Find and set the position of maximum intensity in the ion chamber
    *detector*. The scanning range is relative to the current motor
    position, and will go *distance* above and below it. For example,
    if the current position is 1000, ``distance=200`` will scan from
    800 to 1200.

    Parameters
    ==========
    bec
      A bluesky best effort callback for finding the peak position.
    distance
      Relative distance to scan in either direction.
    reverse
      Whether the scan goes low-to-high (False) or high-to-low (True).
    feature
      Which feature of the peak to use for alignment.
    md
      Extra metadata to pass into the run engine.

    """
    msg = (
        "The ``align_motor`` plan is deprecated. "
        "Consider using ``bluesky.plans.tune_centroid`` instead"
    )
    warnings.warn(msg, DeprecationWarning)
    # Prepare metadata
    md_ = dict(plan_name="align_motor")
    md_.update(md)
    # Set up the best effort callback
    if bec is None:
        bec = best_effort.BestEffortCallback()
        bec.disable_table()
    # Determine plan parameters
    start, end = (distance, -distance) if reverse else (-distance, distance)
    # Resolve motors and detectors
    motor = registry.find(motor)
    det = registry.find(detector)
    detectors = [det]
    if hasattr(det, "raw_counts"):
        detectors.insert(0, det.raw_counts)
    # from pprint import pprint
    # pprint(detectors)
    # print(motor)
    # print(start, end)
    # print(feature)
    # print(bec, md_)
    # assert False
    plan = lineup(
        detectors, motor, start, end, npts=40, feature=feature, bec=bec, md=md_
    )
    plan = subs_wrapper(plan, bec)
    yield from plan
    # Wait for the callback to catch up
    t0 = time.time()
    timeout = 5
    det_name = detectors[0].name
    while time.time() - t0 < timeout:
        new_value = bec.peaks[feature].get(det_name)
        if new_value is not None:
            if feature in ["max", "min"]:
                # Max and min also include the y-value
                new_value, y_value = new_value
            break
    # Set the motor to the new value (from below accounting for hysteresis)
    if new_value is None:
        # Didn't find a peak position
        msg = (
            f"No peak position found for {det_name},"
            f"motor '{motor.name}' will not be set."
        )
        log.error(msg)
        warnings.warn(msg)
    else:
        yield from bps.mv(motor, new_value - abs(end - start) / 2)
        yield from bps.mv(motor, new_value)
