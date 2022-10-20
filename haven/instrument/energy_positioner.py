from ophyd import (
    PseudoPositioner,
    EpicsMotor,
    Component as Cpt,
    FormattedComponent as FCpt,
    PseudoSingle,
    PVPositioner,
    EpicsSignal,
    EpicsSignalRO,
)
from ophyd.pseudopos import pseudo_position_argument, real_position_argument
import epics
from apstools.devices import ApsUndulator

from ..signal import Signal
from .._iconfig import load_config
from .monochromator import monochromator


class Undulator(PVPositioner):
    setpoint = Cpt(EpicsSignal, ":ScanEnergy.VAL")
    readback = Cpt(EpicsSignalRO, ":Energy.RBV")
    done = Cpt(EpicsSignalRO, ":Busy.VAL")
    stop_signal = Cpt(EpicsSignal, ":Stop.VAL")


class EnergyPositioner(PseudoPositioner):
    # Pseudo axes
    energy = Cpt(PseudoSingle)

    # Equivalent real axes
    mono_energy = FCpt(EpicsMotor, "{mono_energy_pv}")
    id_energy = FCpt(Undulator, "{id_prefix}")

    def __init__(self, mono_energy_pv, id_prefix, *args, **kwargs):
        self.mono_energy_pv = mono_energy_pv
        self.id_prefix = id_prefix
        super().__init__(*args, **kwargs)

    @pseudo_position_argument
    def forward(self, target_energy):
        "Given a target energy, transform to the mono and ID energies."
        return self.RealPosition(
            mono_energy=target_energy.energy,
            id_energy=target_energy.energy + 100,
        )

    @real_position_argument
    def inverse(self, device_energy):
        "Given a position in mono and ID energy, transform to the target energy."
        return self.PseudoPosition(
            energy=device_energy.mono_energy,
        )


energy_positioner = EnergyPositioner(
    name="energy",
    mono_energy_pv=monochromator.energy.prefix,
    id_prefix=load_config()["undulator"]["ioc"],
)
