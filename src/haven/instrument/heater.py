import asyncio
import logging

from apstools.devices import PTC10AioChannel as PTC10AioChannelBase
from apstools.devices import PTC10PositionerMixin, PTC10TcChannel
from ophyd import Component as Cpt
from ophyd import EpicsSignalRO, EpicsSignalWithRBV, PVPositioner

from .._iconfig import load_config
from .device import aload_devices, make_device

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


def load_heater_coros(config=None):
    if config is None:
        config = load_config()
    # Load the heaters
    for name, cfg in config.get("heater", {}).items():
        Cls = globals().get(cfg["device_class"])
        yield make_device(
            Cls, prefix=f"{cfg['prefix']}:", name=name, labels={"heaters"}
        )


def load_heaters(config=None):
    return asyncio.run(aload_devices(*load_heater_coros(config=config)))
