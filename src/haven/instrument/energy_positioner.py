import logging
from typing import Mapping

from ophyd import Component as Cpt
from ophyd import EpicsMotor, EpicsSignal, EpicsSignalRO
from ophyd import FormattedComponent as FCpt
from ophyd import PseudoPositioner, PseudoSingle, PVPositionerPC, PVPositioner, Signal
from ophyd.ophydobj import OphydObject
from ophyd.pseudopos import pseudo_position_argument, real_position_argument
from pcdsdevices.signal import MultiDerivedSignal

from .._iconfig import load_config
from .device import make_device
from .monochromator import Monochromator
from .xray_source import PlanarUndulator

log = logging.getLogger(__name__)


__all__ = ["EnergyPositioner", "load_energy_positioner"]


class EnergyPositioner(PVPositionerPC):
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
    mono_prefix
      The CA prefix for the monochromator IOC.
    undulator_prefix
      The prefix for the insertion device energy, such that
      f"{id_prefix}:Energy.VAL" reaches the energy readback value.

    """

    # Individual energy components
    monochromator = FCpt(Monochromator, "{mono_prefix}")
    undulator = FCpt(PlanarUndulator, "{undulator_prefix}")

    # Equivalent real axes
    # mono_energy: OphydObject = FCpt(EpicsMotor, "{mono_pv}", kind="normal")
    # id_offset: float = 300.  # In eV
    # id_tracking: OphydObject = FCpt(EpicsSignal, "{id_tracking_pv}", kind="config")
    # id_offset: OphydObject = FCpt(EpicsSignal, "{id_offset_pv}", kind="config")
    # id_energy: OphydObject = FCpt(Undulator, "{id_prefix}", kind="normal")

    def __init__(
        self,
        mono_prefix: str,
        undulator_prefix: str,
        *args,
        **kwargs,
    ):
        self.mono_prefix = mono_prefix
        self.undulator_prefix = undulator_prefix
        super().__init__(*args, **kwargs)

    def set_energy(self, *, mds: MultiDerivedSignal, value: float):
        offset = self.monochromator.id_offset.get()
        vals = {
            self.monochromator.energy: value,
            self.undulator.energy: value + offset,
        }
        return vals

    def get_energy(self, mds: MultiDerivedSignal, items: Mapping):
        if self.monochromator.energy.user_readback in items:
            energy = items[self.monochromator.energy.user_readback]
        else:
            energy = items[self.monochromator.energy.user_setpoint]
        return energy

    setpoint = Cpt(
        MultiDerivedSignal,
        attrs={"monochromator.energy.user_setpoint", "undulator.energy.setpoint"},
        calculate_on_get=get_energy,
        calculate_on_put=set_energy,
        name="setpoint",
    )
    readback = Cpt(
        MultiDerivedSignal,
        attrs={"monochromator.energy.user_readback"},
        calculate_on_get=get_energy,
        calculate_on_put=set_energy,
        name="readback",
    )
    # readback = Cpt(MultiDerivedSignal, name="readback")

    # @pseudo_position_argument
    # def forward(self, target_energy):
    #     "Given a target energy, transform to the mono and ID energies."
    #     id_offset_ev = self.id_offset.get(use_monitor=True)
    #     return self.RealPosition(
    #         mono_energy=target_energy.energy,
    #         id_energy=(target_energy.energy + id_offset_ev) / 1000.0,
    #     )

    # @real_position_argument
    # def inverse(self, device_energy):
    #     "Given a position in mono and ID energy, transform to the target energy."
    #     return self.PseudoPosition(
    #         energy=device_energy.mono_energy,
    #     )


def load_energy_positioner(config=None):
    # Load PV's from config
    if config is None:
        config = load_config()
    # Guard to make sure we have a mono and ID configuration
    if "monochromator" not in config.keys() or "undulator" not in config.keys():
        return
    # Extract PVs from config
    undulator_prefix = config["undulator"]["ioc"]
    # id_offset_suffix = Monochromator.id_offset.suffix
    # id_tracking_suffix = Monochromator.id_tracking.suffix
    # Make the combined energy device
    return make_device(
        EnergyPositioner,
        name="energy",
        mono_prefix=config["monochromator"]["prefix"],
        # id_offset_pv=f"{mono_prefix}{id_offset_suffix}",
        # id_tracking_pv=f"{mono_prefix}{id_tracking_suffix}",
        undulator_prefix=undulator_prefix,
    )


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
