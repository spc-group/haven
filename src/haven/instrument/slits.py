import asyncio
import logging

from apstools.synApps.db_2slit import Optics2Slit2D_HV

from .._iconfig import load_config
from .device import aload_devices, await_for_connection, make_device
from .instrument_registry import registry

log = logging.getLogger(__name__)


async def make_slits_device(prefix, name):
    slits = Optics2Slit2D_HV(prefix=prefix, name=name, labels={"slits"})
    try:
        await await_for_connection(slits)
    except TimeoutError as exc:
        log.warning(f"Could not connect to slits: {name} ({prefix})")
    else:
        log.info(f"Created slits: {name} ({prefix})")
        registry.register(slits)
        return slits


def load_slit_coros(config=None):
    if config is None:
        config = load_config()
    # Create slits
    for name, slit_config in config.get("slits", {}).items():
        yield make_device(Optics2Slit2D_HV, prefix=slit_config["prefix"], name=name, labels={"slits"})


def load_slits(config=None):
    asyncio.run(aload_devices(*load_slit_coros(config=config)))
