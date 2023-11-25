"""This is a copy of the apstools Slits support with signals for the tweak PV."""


import asyncio
import logging

from ophyd import FormattedComponent as FCpt, Component as Cpt
from ophyd import Device
from ophyd import EpicsSignal
from apstools.synApps.db_2slit import Optics2Slit2D_HV
from apstools.devices import PVPositionerSoftDone
from apstools.utils import SlitGeometry

from .._iconfig import load_config
from .device import aload_devices, await_for_connection, make_device
from .instrument_registry import registry

log = logging.getLogger(__name__)


class PVPositionerWithTweaks(PVPositionerSoftDone):
    tweak_value = FCpt(EpicsSignal, "{prefix}{_setpoint_pv}_tweakVal.VAL")
    tweak_forward = FCpt(EpicsSignal, "{prefix}{_setpoint_pv}_tweak.B")
    tweak_reverse = FCpt(EpicsSignal, "{prefix}{_setpoint_pv}_tweak.A")


class Optics2Slit1D(Device):
    """
    EPICS synApps optics 2slit.db 1D support: xn, xp, size, center, sync

    "sync" is used to tell the EPICS 2slit database to synchronize the
    virtual slit values with the actual motor positions.
    """

    xn = Cpt(PVPositionerWithTweaks, "", setpoint_pv="xn", readback_pv="t2.B")
    xp = Cpt(PVPositionerWithTweaks, "", setpoint_pv="xp", readback_pv="t2.A")
    size = Cpt(PVPositionerWithTweaks, "", setpoint_pv="size", readback_pv="t2.C")
    center = Cpt(PVPositionerWithTweaks, "", setpoint_pv="center", readback_pv="t2.D")

    sync = Cpt(EpicsSignal, "sync", put_complete=True, kind="omitted")


class Optics2Slit2D_HV(Device):
    """
    EPICS synApps optics 2slit.db 2D support: h.xn, h.xp, v.xn, v.xp
    """

    h = Cpt(Optics2Slit1D, "H")
    v = Cpt(Optics2Slit1D, "V")

    @property
    def geometry(self):
        """Return the slit 2D size and center as a namedtuple."""
        pppp = [
            round(obj.position, obj.precision) for obj in (self.h.size, self.v.size, self.h.center, self.v.center)
        ]

        return SlitGeometry(*pppp)

    @geometry.setter
    def geometry(self, value):
        # first, test the input by assigning it to local vars
        width, height, x, y = value

        self.h.size.move(width)
        self.v.size.move(height)
        self.h.center.move(x)
        self.v.center.move(y)


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
