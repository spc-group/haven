import logging
import asyncio
from apstools.devices.aps_undulator import ApsUndulator
import epics

from .instrument_registry import registry
from .._iconfig import load_config
from .device import await_for_connection, aload_devices


log = logging.getLogger(__name__)


async def make_xray_device(prefix: str):
    dev = ApsUndulator(prefix=prefix, name="undulator", labels={"xray_sources"})
    print(epics.caget("ID255:Energy"))
    try:
        await await_for_connection(dev)
    except TimeoutError as exc:
        msg = f"Could not connect to xray source: {prefix}"
        log.warning(msg)
    else:
        registry.register(dev)
        return dev


def load_xray_source_coros(config=None):
    if config is None:
        config = load_config()
    # Determine the X-ray source type (undulator vs bending magnet)
    data = config["xray_source"]
    if data["type"] == "undulator":
        yield make_xray_device(prefix=data["prefix"])


def load_xray_sources(config=None):
    asyncio.run(aload_devices(*load_xray_source_coros(config=config)))
