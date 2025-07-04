import numpy as np
from scipy import constants
from pint import Quantity, UnitRegistry

ureg = UnitRegistry()

h = (
    constants.physical_constants["Planck constant in eV/Hz"][0]
    * ureg.electron_volt
    / ureg.hertz
)
c = constants.c * ureg.meter / ureg.second


def energy_to_wavelength(energy: Quantity) -> Quantity:
    """Energy in eV to wavelength in meters."""
    return h * c / energy


wavelength_to_energy = energy_to_wavelength


def bragg_to_wavelength(bragg_angle: Quantity, d: Quantity, n: int = 1) -> Quantity:
    """Convert Bragg angle to wavelength.

    Parameters
    ==========
    bragg_angle
      The Bragg angle (θ) of the reflection.
    d
      Inter-planar spacing of the crystal.
    n
      The order of the reflection.
    """
    return 2 * d * np.sin(bragg_angle) / n


def wavelength_to_bragg(wavelength: Quantity, d: Quantity, n: int = 1) -> Quantity:
    """Convert wavelength to Bragg angle.

    Parameters
    ==========
    wavelength
      The photon wavelength in meters.
    d
      Inter-planar spacing of the crystal.
    n
      The order of the reflection.

    Returns
    =======
    bragg
      The Bragg angle of the reflection, in Radians.
    """
    return np.arcsin(n * wavelength / 2 / d)


def energy_to_bragg(energy: Quantity, d: Quantity) -> Quantity:
    """Convert photon energy to Bragg angle.

    Parameters
    ==========
    energy
      Photon energy, in eV.
    d
      d-spacing of the analyzer crystal, in meters.

    Returns
    =======
    bragg
      First order Bragg angle for this photon, in radians.

    """
    bragg = np.arcsin(h * c / 2 / d / energy)
    return bragg


def bragg_to_energy(bragg: Quantity, d: Quantity) -> Quantity:
    """Convert Bragg angle to photon energy.

    Parameters
    ==========
    bragg
      Bragg angle for the crystal.
    d
      d-spacing of the analyzer crystal.

    Returns
    =======
    energy
      Photon energy.

    """
    energy = h * c / 2 / d / np.sin(bragg)
    return energy
