from dataclasses import dataclass

import numpy as np
import pint
from scipy import constants

__all__ = ["ERange", "KRange"]


DEFAULT_EXPOSURE = 0.5

# Calculate the conversion coefficient from k -> eV
ureg = pint.UnitRegistry()
hbar = constants.hbar * ureg.joule * ureg.second
c = constants.speed_of_light * ureg.meter / ureg.second
m_e = (
    constants.physical_constants["electron mass energy equivalent in MeV"][0]
    * 1e6
    * ureg.electron_volt
)
ALPHA = hbar**2 * c**2 / 2 / m_e
ALPHA = ALPHA.to("electron_volt * angstrom * angstrom").magnitude


@dataclass
class EnergyRange:
    """A range of energies used for scanning."""

    def energies(self):
        raise NotImplementedError

    def exposures(self):
        raise NotImplementedError


@dataclass
class ERange(EnergyRange):
    """A range of energies used for scanning.

    All values are assumed to be in electron-volts. If *E0* is a

    Parameters
    ==========

    E_min
      Starting energy of the range, in eV.
    E_max
      Ending energy of the range, in eV.
    E_step
      Step-size between energies, in eV.
    exposure
      How long to spend at each energy, in seconds.

    """

    E_min: float
    E_max: float
    E_step: float = 1.0
    exposure: float = DEFAULT_EXPOSURE

    def energies(self):
        """Convert the range to a sequence of actual energy values, in eV."""
        return np.arange(self.E_min, self.E_max + self.E_step, self.E_step)

    def exposures(self):
        """Convert the range to a sequence of exposure times, in seconds."""
        return [self.exposure] * len(self.energies())


@dataclass
class KRange(EnergyRange):
    """A range of energies used for scanning in the EXAFS region.

    Values are a mix of electron-volts and K-space values.

    Parameters
    ==========

    k_min
      Ending energy of the range, in Å⁻.
    k_max
      Ending energy of the range, in Å⁻.
    k_step
      Step-size between energies, in Å⁻.
    k_weight
      Weighting factor for longer exposures at higher energies.
    exposure
      How long to spend at each energy, in seconds.

    """

    k_min: float
    k_max: float
    k_step: float = 0.1
    k_weight: float = 0.0
    exposure: float = DEFAULT_EXPOSURE

    def energies(self):
        """Calculates photon energies in units of eV."""
        return self.wavenumber_to_energy(self.wavenumbers())

    def energy_to_wavenumber(self, energy):
        return np.sqrt(energy / ALPHA)

    def wavenumber_to_energy(self, wavenumber):
        return wavenumber**2 * ALPHA

    def wavenumbers(self):
        """Calculates wavenumbers (k) for the photo-electron in units Å⁻."""
        k_min = self.energy_to_wavenumber(self.E_min)
        ks = np.arange(k_min, self.k_max + self.k_step, self.k_step)
        return ks

    def exposures(self):
        ks = self.wavenumbers()
        return self.exposure * (ks / np.min(ks)) ** self.k_weight


def merge_ranges(*ranges, default_exposure=DEFAULT_EXPOSURE):
    """Combine multiple energy ranges.

    If any of *ranges* is a instance of ``EnergyRange`` or one of its
    subclasses, then the object will be decomposed to it's constituent
    energies and exposure times. Otherwise, the value will be used
    as-is for the list of energies, and *default_exposure* will be
    used for the exposure time.

    Results will be sorted by energy, and redundant energies will be
    removed with the exposure time being taken from the first instance
    of the particular energy encountered.

    Returns
    =======
    energies
      A sequence of energies, in eV.
    exposures
      A sequence of exposure times, in seconds.

    """
    energies = []
    exposures = []
    for rng in ranges:
        if not isinstance(rng, EnergyRange):
            # Not an energy range, assume it's a float or something
            energies.append(rng)
            exposures.append(default_exposure)
        else:
            # An energy range, so break it down
            energies.extend(rng.energies())
            exposures.extend(rng.exposures())
    # Convert to proper arrays, and remove duplicate energies
    energies, unique_idx = np.unique(
        np.asarray(energies, dtype=float), return_index=True
    )
    exposures = np.asarray(exposures, dtype=float)[unique_idx]
    return energies, exposures


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
