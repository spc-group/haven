import logging
import asyncio
from bluesky import suspenders
from ophyd import FormattedComponent as FCpt, EpicsSignal
from apstools.devices.shutters import ApsPssShutterWithStatus as Shutter

from .._iconfig import load_config
from .instrument_registry import registry
from .device import await_for_connection, aload_devices, make_device


log = logging.getLogger(__name__)


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
        yield make_device(
            Shutter,
            prefix=f"{prefix}:{acronym}",
            open_pv=f"{prefix}:{acronym}_OPEN_EPICS.VAL",
            close_pv=f"{prefix}:{acronym}_CLOSE_EPICS.VAL",
            state_pv=f"{prefix}:{hutch}_BEAM_PRESENT",
            name=name,
            labels={"shutters"},
        )


def load_shutters(config=None):
    asyncio.run(aload_devices(*load_shutter_coros(config=config)))
