import asyncio
from enum import IntEnum
import logging

from ophyd import (
    Device,
    Component as Cpt,
    FormattedComponent as FCpt,
    EpicsMotor,
    EpicsSignal,
    EpicsSignalRO,
)

from .instrument_registry import registry
from .._iconfig import load_config
from .device import await_for_connection, aload_devices, make_device


log = logging.getLogger(__name__)


class IDTracking(IntEnum):
    OFF = 0
    ON = 1


class Monochromator(Device):
    # ID tracking PVs
    id_tracking = Cpt(EpicsSignal, ":ID_tracking", kind="config")
    id_offset = Cpt(EpicsSignal, ":ID_offset", kind="config")
    d_spacing = Cpt(EpicsSignal, ":dspacing", kind="config")
    # Virtual positioners
    mode = Cpt(EpicsSignal, ":mode", labels={"motors", "baseline"}, kind="config")
    energy = Cpt(EpicsMotor, ":Energy", labels={"motors"}, kind="hinted")
    energy_constant1 = Cpt(
        EpicsSignal, ":EnergyC1.VAL", labels={"baseline"}, kind="config"
    )
    energy_constant2 = Cpt(
        EpicsSignal, ":EnergyC2.VAL", labels={"baseline"}, kind="config"
    )
    energy_constant3 = Cpt(
        EpicsSignal, ":EnergyC3.VAL", labels={"baseline"}, kind="config"
    )
    offset = Cpt(EpicsMotor, ":Offset", labels={"motors", "baseline"}, kind="config")
    # ACS Motors
    horiz = Cpt(EpicsMotor, ":ACS:m1", labels={"motors", "baseline"}, kind="config")
    vert = Cpt(EpicsMotor, ":ACS:m2", labels={"motors", "baseline"}, kind="config")
    bragg = Cpt(EpicsMotor, ":ACS:m3", labels={"motors"})
    gap = Cpt(EpicsMotor, ":ACS:m4", labels={"motors"})
    roll2 = Cpt(EpicsMotor, ":ACS:m5", labels={"motors", "baseline"}, kind="config")
    pitch2 = Cpt(EpicsMotor, ":ACS:m6", labels={"motors", "baseline"}, kind="config")
    roll_int = Cpt(EpicsMotor, ":ACS:m7", labels={"motors", "baseline"}, kind="config")
    pi_int = Cpt(EpicsMotor, ":ACS:m8", labels={"motors", "baseline"}, kind="config")
    # Physical constants
    d_spacing = Cpt(EpicsSignalRO, ":dspacing", labels={"baseline"}, kind="config")


def load_monochromator_coros(config=None):
    # Load PV's from config
    if config is None:
        config = load_config()
    prefix = config["monochromator"]["ioc"]
    yield make_device(
        Monochromator, name="monochromator", labels={"monochromators"}, prefix=prefix
    )


def load_monochromator(config=None):
    asyncio.run(aload_devices(*load_monochromator_coros(config=config)))
