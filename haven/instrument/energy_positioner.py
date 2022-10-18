from ophyd import PseudoPositioner, EpicsMotor, Component as Cpt, FormattedComponent as FCpt, PseudoSingle
from ophyd.pseudopos import (pseudo_position_argument,
                             real_position_argument)
import epics

from ..signal import Signal
from .._iconfig import load_config
from .monochromator import monochromator


class EnergyPositioner(PseudoPositioner):
    # Pseudo axes
    energy = Cpt(PseudoSingle)

    # Equivalent real axes
    mono_energy = FCpt(EpicsMotor, "{mono_energy_pv}")
    # id_energy = FCpt(Signal, "{id_prefix}:Scanenergy")

    def __init__(self, mono_energy_pv, id_prefix, *args, **kwargs):
        self.mono_energy_pv = mono_energy_pv
        self.id_prefix = id_prefix
        super().__init__(*args, **kwargs)

    @pseudo_position_argument
    def forward(self, target_energy):
        "Given a target energy, transform to the mono and ID energies."
        return self.RealPosition(
            mono_energy=target_energy.energy
        )
        # return self.RealPosition(
        #     real1=-pseudo_pos.pseudo1,
        #     real2=-pseudo_pos.pseudo2,
        #     real3=-pseudo_pos.pseudo3
        # )

    @real_position_argument
    def inverse(self, device_energy):
        "Given a position in mono and ID energy, transform to the target energy."
        return self.PseudoPosition(
            energy=device_energy.mono_energy,
        )
        # return self.PseudoPosition(
        #     pseudo1=-real_pos.real1,
        #     pseudo2=-real_pos.real2,
        #     pseudo3=-real_pos.real3
        # )


energy_positioner = EnergyPositioner(name="energy",
                                     mono_energy_pv=monochromator.energy.prefix,
                                     id_prefix=load_config()["undulator"]["ioc"])
