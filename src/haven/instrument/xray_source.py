import asyncio
import logging

import epics
from apstools.devices.aps_undulator import ApsUndulator

from .._iconfig import load_config
from .device import aload_devices, await_for_connection, make_device
from .instrument_registry import registry

log = logging.getLogger(__name__)


def load_xray_source_coros(config=None):
    if config is None:
        config = load_config()
    # Determine the X-ray source type (undulator vs bending magnet)
    data = config["xray_source"]
    if data["type"] == "undulator":
        yield make_device(
            ApsUndulator,
            prefix=data["prefix"],
            name="undulator",
            labels={"xray_sources"},
        )


def load_xray_sources(config=None):
    asyncio.run(aload_devices(*load_xray_source_coros(config=config)))
