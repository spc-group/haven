from bluesky import plans as bp, plan_stubs as bps

from .shutters import open_shutters, close_shutters
from ..instrument.instrument_registry import registry

def record_dark_current(ion_chambers, shutters, time):
    """Record the dark current on the ion chambers.

    - Close shutters
    - Record ion chamber dark current
    - Open shutters

    Parameters
    ==========
    ion_chambers
      Ion chamber devices or names.
    shutters
      Shutter devices or names.

    """
    yield from close_shutters(shutters)
    # Measure the dark current
    ion_chambers = registry.findall(ion_chambers)
    # This is a big hack, we need to come back and just accept the current integration time
    old_times = [ic.exposure_time.get() for ic in ion_chambers]
    time_args = [obj for ic in ion_chambers for obj in (ic.record_dark_time, time)]
    yield from bps.mv(*time_args)
    mv_args = [obj for ic in ion_chambers for obj in (ic.record_dark_current, 1)]
    triggers = [ic.record_dark_current for ic in ion_chambers]    
    yield from bps.mv(*mv_args)
    yield from bps.sleep(time)
    time_args = [obj for (ic, t) in zip(ion_chambers, old_times) for obj in (ic.exposure_time, t)]
    yield from bps.mv(*time_args)
    # Open shutters again
    yield from open_shutters(shutters)
