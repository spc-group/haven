import logging

from ophyd import PVPositioner, EpicsSignalRO, EpicsSignalWithRBV, Component as Cpt
from apstools.devices import (
    PTC10PositionerMixin,
    PTC10AioChannel as PTC10AioChannelBase,
    PTC10TcChannel,
)

from .._iconfig import load_config
from .instrument_registry import registry
from .device import await_for_connection


log = logging.getLogger(__name__)


# The apstools version uses "voltage_RBV" as the PVname
class PTC10AioChannel(PTC10AioChannelBase):
    """
    SRS PTC10 AIO module
    """

    voltage = Cpt(EpicsSignalRO, "output_RBV", kind="config")


class CapillaryHeater(PTC10PositionerMixin, PVPositioner):
    readback = Cpt(EpicsSignalRO, "2A:temperature", kind="hinted")
    setpoint = Cpt(EpicsSignalWithRBV, "5A:setPoint", kind="hinted")

    # Additional modules installed on the PTC10
    pid = Cpt(PTC10AioChannel, "5A:")
    tc = Cpt(PTC10TcChannel, "2A:")


async def make_heater_device(Cls, prefix, name):
    heater = Cls(prefix=prefix, name=name, labels={"heaters"})
    try:
        await await_for_connection(heater)
    except TimeoutError as exc:
        log.warning(f"Could not connect to heater: {name} ({prefix})")
    else:
        log.info(f"Created heater: {name} ({prefix})")
        registry.register(heater)
        return heater


def load_heater_coros(config=None):
    if config is None:
        config = load_config()
    # Load the heaters
    coros = set()
    for name, cfg in config.get("heater", {}).items():
        Cls = globals().get(cfg["device_class"])
        coros.add(make_heater_device(Cls=Cls, prefix=f"{cfg['prefix']}:", name=name))
    return coros
