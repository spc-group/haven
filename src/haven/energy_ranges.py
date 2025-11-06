import math
from dataclasses import astuple, dataclass

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


def energy_to_wavenumber(energy: float, relative_to: float = 0.0):
    """Convert a wavenumber (eV) to energy (Å⁻).

    *relative_to* can be used to calculate step sizes, e.g
    ``wavenumber_to_energy(700, relative_to=50)`` calculates the size
    in eV of the step between 50 eV and 70 eV.

    """
    kref = np.sqrt(relative_to / ALPHA)
    print(energy, ALPHA)
    k = np.sqrt(energy / ALPHA)
    return k - kref


def wavenumber_to_energy(wavenumber: float, relative_to: float = 0.0):
    """Convert a wavenumber (Å⁻) to energy (eV).

    *relative_to* can be used to calculate step sizes, e.g
    ``wavenumber_to_energy(2.5, relative_to=2.0)`` calculates the size
    in eV of the step between 2.0Å⁻ and 2.5Å⁻.

    """
    E = wavenumber**2 * ALPHA
    E0 = relative_to**2 * ALPHA
    return E - E0


def round_to_int(num):
    digits = -int(math.log10(math.ulp(num)))
    return int(round(num, digits))


@dataclass(eq=True, frozen=True)
class EnergyRange:
    """A range of energies used for scanning."""

    start: float
    stop: float
    step: float = 1.0
    exposure: float = DEFAULT_EXPOSURE

    def energies(self):
        raise NotImplementedError

    def exposures(self):
        raise NotImplementedError


def from_tuple(energy_range):
    """Convert tuple of (start, stop, step?, exposure?, weight?) to energy range."""
    if isinstance(energy_range, EnergyRange):
        return energy_range
    if energy_range[0] in ["E", "e"]:
        return ERange(*energy_range[1:])
    if energy_range[0] in ["k", "K"]:
        return KRange(*energy_range[1:])
    return ERange(*energy_range)


def full_range(start, end, step):
    """Calculate a range, but inclusive of start and end (if a multiple of
    the step).

    """

    num_steps = round_to_int((end - start) / step)
    lin_max = start + num_steps * step
    return np.linspace(start, lin_max, num=num_steps + 1)


@dataclass(eq=True, frozen=True)
class ERange(EnergyRange):
    """A range of energies used for scanning.

    All values are assumed to be in electron-volts. If *E0* is a

    Parameters
    ==========

    start
      Starting energy of the range, in eV.
    stop
      Ending energy of the range, in eV.
    step
      Step-size between energies, in eV.
    exposure
      How long to spend at each energy, in seconds.

    """

    def astuple(self):
        return ("E", *astuple(self))

    def energies(self):
        """Convert the range to a sequence of actual energy values, in eV."""
        return full_range(self.start, self.stop, self.step)

    def exposures(self):
        """Convert the range to a sequence of exposure times, in seconds."""
        return self.exposure * self.energies() ** 0  # do not consider weights for now


@dataclass(eq=True, frozen=True)
class KRange(EnergyRange):
    """A range of energies used for scanning in the EXAFS region.

    Values are a mix of electron-volts and K-space values.

    Parameters
    ==========

    start
      Starting energy of the range, in Å⁻.
    stop
      Ending energy of the range, in Å⁻.
    step
      Step-size between energies, in Å⁻.
    exposure
      How long to spend at each energy, in seconds.
    weight
      Weighting factor for longer exposures at higher energies.

    """

    weight: float = 0.0

    def astuple(self):
        return ("K", *astuple(self))

    def energies(self):
        """Calculates photon energies in units of eV."""
        return wavenumber_to_energy(self.wavenumbers())

    def wavenumbers(self):
        """Calculates wavenumbers (k) for the photo-electron in units Å⁻."""
        ks = full_range(self.start, self.stop, self.step)
        return ks

    def exposures(self):
        ks = self.wavenumbers()
        return self.exposure * ((ks / np.min(ks)) ** self.weight)


def merge_ranges(*ranges, default_exposure=DEFAULT_EXPOSURE, sort=False):
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

    if sort:
        # sorting energies from small to big
        sorted_indices = np.argsort(energies)
        energies = energies[sorted_indices]
        exposures = exposures[sorted_indices]

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
