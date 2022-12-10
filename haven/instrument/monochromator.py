from ophyd import Device, Component as Cpt, FormattedComponent as FCpt, EpicsMotor, EpicsSignal

from .instrument_registry import registry


@registry.register
class Monochromator(Device):
    horiz = Cpt(EpicsMotor, ":m1", labels={"motors"}, kind="config")
    vert = Cpt(EpicsMotor, ":m2", labels={"motors"}, kind="config")
    bragg = Cpt(EpicsMotor, ":m3", labels={"motors"})
    gap = Cpt(EpicsMotor, ":m4", labels={"motors"})
    roll2 = Cpt(EpicsMotor, ":m5", labels={"motors"}, kind="config")
    pitch2 = Cpt(EpicsMotor, ":m6", labels={"motors"}, kind="config")
    roll_int = Cpt(EpicsMotor, ":m7", labels={"motors"}, kind="config")
    pi_int = Cpt(EpicsMotor, ":m8", labels={"motors"}, kind="config")
    mode = Cpt(EpicsSignal, ":mode", labels={"motors"}, kind="config")
    energy = Cpt(EpicsMotor, ":Energy", labels={"motors"}, kind="hinted")


def load_monochromator(config):
    monochromator = Monochromator(config["monochromator"]["ioc"], name="monochromator")
    return monochromator
