from ophyd import (
    Device,
    Component as Cpt,
    FormattedComponent as FCpt,
    EpicsMotor,
    EpicsSignal,
)

from .instrument_registry import registry
from .._iconfig import load_config


@registry.register
class Monochromator(Device):
    # ID tracking PVs
    id_tracking = Cpt(EpicsSignal, ":ID_tracking", kind="config")
    id_offset = Cpt(EpicsSignal, ":ID_offset", kind="config")
    d_spacing = Cpt(EpicsSignal, ":dspacing", kind="config")
    # Virtual positioners
    mode = Cpt(EpicsSignal, ":mode", labels={"motors"}, kind="config")
    energy = Cpt(EpicsMotor, ":Energy", labels={"motors"}, kind="hinted")
    offset = Cpt(EpicsMotor, ":Offset", labels={"motors"}, kind="config")
    # ACS Motors
    horiz = Cpt(EpicsMotor, ":ACS:m1", labels={"motors"}, kind="config")
    vert = Cpt(EpicsMotor, ":ACS:m2", labels={"motors"}, kind="config")
    bragg = Cpt(EpicsMotor, ":ACS:m3", labels={"motors"})
    gap = Cpt(EpicsMotor, ":ACS:m4", labels={"motors"})
    roll2 = Cpt(EpicsMotor, ":ACS:m5", labels={"motors"}, kind="config")
    pitch2 = Cpt(EpicsMotor, ":ACS:m6", labels={"motors"}, kind="config")
    roll_int = Cpt(EpicsMotor, ":ACS:m7", labels={"motors"}, kind="config")
    pi_int = Cpt(EpicsMotor, ":ACS:m8", labels={"motors"}, kind="config")


def load_monochromator(config=None):
    # Load PV's from config
    if config is None:
        config = load_config()
    monochromator = Monochromator(config["monochromator"]["ioc"], name="monochromator")
    return monochromator
