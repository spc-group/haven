import logging
from typing import Mapping

from ophyd import Component as Cpt
from ophyd import FormattedComponent as FCpt
from ophyd import PVPositionerPC
from pcdsdevices.signal import MultiDerivedSignal

from .monochromator import Monochromator
from .xray_source import PlanarUndulator

log = logging.getLogger(__name__)


__all__ = ["EnergyPositioner"]


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
    monochromator_prefix
      The CA prefix for the monochromator IOC.
    undulator_prefix
      The prefix for the insertion device energy, such that
      f"{id_prefix}:Energy.VAL" reaches the energy readback value.

    """

    # Individual energy components
    monochromator = FCpt(
        Monochromator, "{monochromator_prefix}", labels={"monochromators"}
    )
    undulator = FCpt(
        PlanarUndulator, "{undulator_prefix}", labels={"undulator", "xray_source"}
    )

    def __init__(
        self,
        monochromator_prefix: str,
        undulator_prefix: str,
        name: str = "energy",
        **kwargs,
    ):
        self.monochromator_prefix = monochromator_prefix
        self.undulator_prefix = undulator_prefix
        super().__init__(name=name, **kwargs)

    def set_energy(self, *, mds: MultiDerivedSignal, value: float):
        ev_per_kev = 1000
        offset = self.monochromator.id_offset.get()
        vals = {
            self.monochromator.energy: value,
            self.undulator.energy: (value + offset) / ev_per_kev,
        }
        return vals

    def get_energy(self, mds: MultiDerivedSignal, items: Mapping):
        if self.monochromator.energy.user_readback in items:
            energy = items[self.monochromator.energy.user_readback]
        else:
            energy = items[self.monochromator.energy.user_setpoint]
        return energy

    @property
    def limits(self):
        hi, low = (None, None)
        for signal in self.setpoint.signals:
            # Update the limits based on this signal
            try:
                new_low, new_hi = signal.limits
            except TypeError:
                continue
            # Account for the keV -> eV conversion for the undulator
            if signal is self.undulator.energy.setpoint:
                new_low *= 1000
                new_hi *= 1000
            hi = min([val for val in (hi, new_hi) if val is not None])
            low = max([val for val in (low, new_low) if val is not None])
        return (low, hi)

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
