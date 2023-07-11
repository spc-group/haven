import logging
from bluesky import suspenders
from ophyd import FormattedComponent as FCpt, EpicsSignal
from apstools.devices.shutters import ApsPssShutterWithStatus as Shutter

from .._iconfig import load_config
from .instrument_registry import registry
from .device import await_for_connection


log = logging.getLogger(__name__)


async def make_shutter_device(prefix, open_pv, close_pv, state_pv, name):
    shutter = Shutter(
        prefix=prefix,
        open_pv=open_pv,
        close_pv=close_pv,
        state_pv=state_pv,
        name=name,
        labels={"shutters"},
    )
    try:
        await await_for_connection(shutter)
    except TimeoutError as exc:
        log.warning(f"Could not connect to shutters: {name} ({prefix})")
    else:
        log.info(f"Created shutter: {name} ({prefix})")
        registry.register(shutter)
        return shutter


def load_shutter_coros(config=None):
    if config is None:
        config = load_config()
    prefix = config["shutter"]["prefix"]
    for name, d in config["shutter"].items():
        if name == "prefix":
            continue
        # Calculate suitable PV values
        hutch = d["hutch"]
        acronym = "FES" if hutch == "A" else f"S{hutch}S"
        yield make_shutter_device(
            prefix=f"{prefix}:{acronym}",
            open_pv=f"{prefix}:{acronym}_OPEN_EPICS.VAL",
            close_pv=f"{prefix}:{acronym}_CLOSE_EPICS.VAL",
            state_pv=f"{prefix}:{hutch}_BEAM_PRESENT",
            name=name,
        )
