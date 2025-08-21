"""Utilities and Bluesky plans for reading and converting units."""

from collections.abc import Generator, Mapping
from typing import Any

import numpy as np
from bluesky import Msg
from bluesky import plan_stubs as bps
from bluesky.bundlers import maybe_await
from bluesky.protocols import Readable
from pint import Quantity, Unit, UnitRegistry
from scipy import constants

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


def read_units(device: Readable) -> Generator[Msg, Mapping | None, Unit]:
    """Read units from a device."""

    # Wrap in a coroutine so we can both sync and async devices
    async def describe() -> Mapping[str, Any]:
        return await maybe_await(device.describe())

    result = yield from bps.wait_for([describe])
    if result is None:
        # Maybe there's no run engine?
        return None
    (task,) = result
    if task.exception() is not None:
        raise task.exception()
    try:
        units = task.result()[device.name]["units"]
    except KeyError:
        raise KeyError(f"Descriptor for {device.name} does not contain 'units'.")
    return ureg.Unit(units)


def read_quantity(device: Readable) -> Generator[Msg, Any, Quantity]:
    value = yield from bps.rd(device)
    units = yield from read_units(device)
    if value is None or units is None:
        return None
    return value * units
