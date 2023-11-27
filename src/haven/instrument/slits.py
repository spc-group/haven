"""This is a copy of the apstools Slits support with signals for the tweak PV."""


import asyncio
import logging

from apstools.devices import PVPositionerSoftDone
from apstools.synApps.db_2slit import Optics2Slit2D_HV
from apstools.utils import SlitGeometry
from ophyd import Component as Cpt
from ophyd import DerivedSignal, Device, EpicsSignal
from ophyd import FormattedComponent as FCpt

from .. import exceptions
from .._iconfig import load_config
from .device import aload_devices, await_for_connection, make_device
from .instrument_registry import registry
from .motor import HavenMotor

log = logging.getLogger(__name__)


class SlitMotor(HavenMotor):
    readback = Cpt(DerivedSignal, derived_from="user_readback")
    setpoint = Cpt(DerivedSignal, derived_from="user_setpoint")


class PVPositionerWithTweaks(PVPositionerSoftDone):
    tweak_value = FCpt(EpicsSignal, "{prefix}{_setpoint_pv}_tweakVal.VAL")
    tweak_forward = FCpt(EpicsSignal, "{prefix}{_setpoint_pv}_tweak.B")
    tweak_reverse = FCpt(EpicsSignal, "{prefix}{_setpoint_pv}_tweak.A")


class BladePair(Device):
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


class BladeSlits(Device):
    """Set of slits with blades that move in and out to control beam size."""

    h = Cpt(BladePair, "H")
    v = Cpt(BladePair, "V")

    @property
    def geometry(self):
        """Return the slit 2D size and center as a namedtuple."""
        pppp = [
            round(obj.position, obj.precision)
            for obj in (self.h.size, self.v.size, self.h.center, self.v.center)
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


class ApertureSlits(Device):
    """A rotating aperture that functions like a set of slits.

    Unlike the blades slits, there are no independent parts to move,
    so each axis only has center and size.

    Based on the 25-ID-A whitebeam slits.

    """

    class SlitAxis(Device):
        size = Cpt(SlitMotor, "Size")
        center = Cpt(SlitMotor, "Center")

    h = Cpt(SlitAxis, "h")
    v = Cpt(SlitAxis, "v")


def load_slit_coros(config=None):
    if config is None:
        config = load_config()
    # Create slits
    for name, slit_config in config.get("slits", {}).items():
        DeviceClass = globals().get(slit_config["device_class"])
        # Check that it's a valid device class
        if DeviceClass is None:
            msg = f"slits.{name}.device_class={slit_config['device_class']}"
            raise exceptions.UnknownDeviceConfiguration(msg)
        yield make_device(
            DeviceClass, prefix=slit_config["prefix"], name=name, labels={"slits"}
        )


def load_slits(config=None):
    asyncio.run(aload_devices(*load_slit_coros(config=config)))
