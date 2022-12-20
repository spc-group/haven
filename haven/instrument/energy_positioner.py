from ophyd import (
    PseudoPositioner,
    EpicsMotor,
    Component as Cpt,
    FormattedComponent as FCpt,
    PseudoSingle,
    PVPositioner,
    EpicsSignal,
    EpicsSignalRO,
    OphydObject
)
from ophyd.pseudopos import pseudo_position_argument, real_position_argument


from .._iconfig import load_config
from .instrument_registry import registry
from .monochromator import Monochromator


__all__ = ["EnergyPositioner", "load_energy_positioner"]


class Undulator(PVPositioner):
    setpoint = Cpt(EpicsSignal, ":ScanEnergy.VAL")
    readback = Cpt(EpicsSignalRO, ":Energy.VAL")
    done = Cpt(EpicsSignalRO, ":Busy.VAL", kind="omitted")
    stop_signal = Cpt(EpicsSignal, ":Stop.VAL", kind="omitted")


class EnergyPositioner(PseudoPositioner):
    """The operational energy of the beamline.

    Responsible for setting both mono and ID energy with an optional
    ID offset. Setting the *energy* component will propagate to both
    real devices and so ``EnergyPositioner().energy`` is a good
    candidate for a positioner for Bluesky plans.

    Currently, the offset between the insertion device and the
    monochromator is fixed. In the future this will be replaced with a
    more sophisticated calculation.

    .. todo::

       Insert functionality to have a non-constant ID offset.

    Attributes
    ==========

    id_offset
      The offset for the insertion device relative to the mono energy.
    energy
      The pseudo positioner for the forward calculation.
    mono_energy
      The real component for the monochromator energy.
    id_energy
      The real component for the insertion device energy.

    Parameters
    ==========
    mono_pv
      The process variable for the monochromator energy PV.
    id_prefix
      The prefix for the insertion device energy, such that
      f"{id_prefix}:Energy.VAL" reaches the energy readback value.

    """
    id_offset: float = 155.  # In eV

    # Pseudo axes
    energy: OphydObject = Cpt(PseudoSingle)

    # Equivalent real axes
    mono_energy: OphydObject = FCpt(EpicsMotor, "{mono_pv}")
    id_energy: OphydObject = FCpt(Undulator, "{id_prefix}")

    def __init__(self, mono_pv: str, id_prefix: str, *args, **kwargs):
        """INIT DOCSTRING"""
        self.mono_pv = mono_pv
        self.id_prefix = id_prefix
        super().__init__(*args, **kwargs)

    @pseudo_position_argument
    def forward(self, target_energy):
        "Given a target energy, transform to the mono and ID energies."
        return self.RealPosition(
            mono_energy=target_energy.energy,
            id_energy=(target_energy.energy + self.id_offset) / 1000.0,
        )

    @real_position_argument
    def inverse(self, device_energy):
        "Given a position in mono and ID energy, transform to the target energy."
        return self.PseudoPosition(
            energy=device_energy.mono_energy,
        )


def load_energy_positioner(config=None):
    # Load PV's from config
    if config is None:
        config = load_config()
    mono_suffix = Monochromator.energy.suffix
    mono_prefix = config["monochromator"]["ioc"]
    id_prefix = config["undulator"]["ioc"]
    # Create energy positioner
    energy_positioner = EnergyPositioner(
        name="energy",
        mono_pv=f"{mono_prefix}{mono_suffix}",
        id_prefix=id_prefix,
    )
    registry.register(energy_positioner)
