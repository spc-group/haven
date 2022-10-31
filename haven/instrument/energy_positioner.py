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
from .instrument_registry import registry
from .monochromator import Monochromator


class Undulator(PVPositioner):
    setpoint = Cpt(EpicsSignal, ":ScanEnergy.VAL")
    readback = Cpt(EpicsSignalRO, ":Energy.VAL")
    done = Cpt(EpicsSignalRO, ":Busy.VAL", kind="omitted")
    stop_signal = Cpt(EpicsSignal, ":Stop.VAL", kind="omitted")


# @registry.register
class EnergyPositioner(PseudoPositioner):
    id_offset = 155 # In eV
    
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
            id_energy=(target_energy.energy + self.id_offset) / 1000.,
        )

    @real_position_argument
    def inverse(self, device_energy):
        "Given a position in mono and ID energy, transform to the target energy."
        return self.PseudoPosition(
            energy=device_energy.mono_energy,
        )


def load_energy_positioner(config=None):
    if config is None:
        config = load_config()
    mono_energy_pv = Monochromator.energy.suffix
    energy_ioc = config["monochromator"]["energy_ioc"]
    mono_energy_pv = mono_energy_pv.format(energy_prefix=energy_ioc)
    energy_positioner = EnergyPositioner(
        name="energy",
        mono_energy_pv=mono_energy_pv,
        id_prefix=config["undulator"]["ioc"],
    )
    registry.register(energy_positioner)
