from ophyd import Device, Component as Cpt, FormattedComponent as FCpt, EpicsMotor

from .instrument_registry import registry


@registry.register
class Monochromator(Device):
    horiz = Cpt(EpicsMotor, ":m1", kind="config")
    vert = Cpt(EpicsMotor, ":m2", kind="config")
    bragg = Cpt(EpicsMotor, ":m3")
    gap = Cpt(EpicsMotor, ":m4")
    roll2 = Cpt(EpicsMotor, ":m5", kind="config")
    pitch2 = Cpt(EpicsMotor, ":m6", kind="config")
    roll_int = Cpt(EpicsMotor, ":m7", kind="config")
    pi_int = Cpt(EpicsMotor, ":m8", kind="config")
    mode = Cpt(EpicsMotor, ":mode", kind="config")
    energy = FCpt(EpicsMotor, "{energy_prefix}:Energy")

    def __init__(
        self, prefix, *args, name, energy_prefix=None, id_prefix=None, **kwargs
    ):
        # Use the default ioc for energy if not explicitly set
        if energy_prefix is None:
            energy_prefix = prefix
        self.energy_prefix = energy_prefix
        self.id_prefix = id_prefix
        super().__init__(prefix, name=name, *args, **kwargs)


def load_monochromator(config):
    monochromator = Monochromator(
        config["monochromator"]["ioc"],
        energy_prefix=config["monochromator"]["energy_ioc"],
        name="monochromator",
    )
    return monochromator
