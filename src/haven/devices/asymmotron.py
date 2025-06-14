"""More calculations from Yanna.

def theta_bragg(energy_val, hkl=[4,4,4]):
    d_spacing = lattice_cons / np.sqrt(hkl[0] ** 2 + hkl[1] ** 2 + hkl[2] ** 2)
    theta_bragg_val = np.arcsin(hc / (energy_val * 2 * d_spacing))
    theta_bragg_val = np.degrees(theta_bragg_val)
    return theta_bragg_val


Some sane values for converting hkl and [HKL] to α:

(001), (101), 90°
(001), (110), 180°

"""

import asyncio
import logging
from typing import TypedDict

import numpy as np
from bluesky.protocols import Movable
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    AsyncStatus,
    DerivedSignalFactory,
    Device,
    LazyMock,
    SignalR,
    StandardReadable,
    StandardReadableFormat,
    Transform,
    derived_signal_r,
    soft_signal_r_and_setter,
    soft_signal_rw,
)
from ophyd_async.epics.motor import Motor
from pint import Quantity, UnitRegistry
from pydantic import ConfigDict
from scipy import constants

from ..positioner import Positioner
from .motor import Motor

__all__ = ["Analyzer", "HKL"]

ureg = UnitRegistry()

log = logging.getLogger(__name__)

um_per_mm = 1000


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


async def device_units(device: SignalR | StandardReadable):
    """Figure out the most likely units to use for *device*.

    Defaults to meters if no other unit can be found."""
    if hasattr(device, "motor_egu"):
        egu = await device.motor_egu.get_value()
    else:
        # Probably a signal
        desc = (await device.describe())[device.name]
        if "units" in desc:
            egu = desc["units"]
        else:
            egu = "m"
    return ureg(egu).units


def units(quantity: Quantity) -> str:
    return str(quantity.to_reduced_units())


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


def hkl_to_alpha(base, reflection) -> Quantity:
    cos_alpha = (
        np.dot(base, reflection) / np.linalg.norm(base) / np.linalg.norm(reflection)
    )
    if cos_alpha > 1:
        cos_alpha = 1
    alpha = np.arccos(cos_alpha) * ureg.radians
    return alpha


class HKL(StandardReadable, Movable):
    """A set of (h, k, l) for a lattice plane.

    Settable as ``hkl.set('312')``, which will set ``hkl.h``,
    ``hkl.k``, and ``hkl.l``.

    """

    def __init__(self, initial_value, name=""):
        h, k, l = self._to_tuple(initial_value)
        with self.add_children_as_readables():
            self.h = soft_signal_rw(int, initial_value=h)
            self.k = soft_signal_rw(int, initial_value=k)
            self.l = soft_signal_rw(int, initial_value=l)

        super().__init__(name=name)

    def _to_tuple(self, hkl_str) -> tuple[str, str, str]:
        h, k, l = hkl_str
        return (h, k, l)

    @AsyncStatus.wrap
    async def set(self, value):
        h, k, l = self._to_tuple(value)
        await asyncio.gather(
            self.h.set(h),
            self.k.set(k),
            self.l.set(l),
        )


class Analyzer(StandardReadable):
    """A single asymmetric analyzer crystal mounted on an Rowland circle.

    **Units** are handled automatically based on units set in EPICS
    PVs. However, the following values are used as parameters when
    creating the analyzer, and are assumed to have the following
    units.

    - rowland_diameter: meters
    - lattice_constant: nanometers
    - wedge_angle: degrees

    Parameters
    ==========
    horizontal_motor_prefix
      The PV prefix for the motor moving the crystal inboard/outboard.
    vertical_motor_prefix
      The PV prefix for the motor moving the crystal closer to the
      ceiling.
    yaw_motor_prefix
      The PV prefix for the motor rotating the crystal around its
      optical axis.
    rowland_diameter
      The diameter of the Rowland circle.
    lattice_constant
      The lattice constant of the analyzer (e.g. Si 111) crystal.
    wedge_angle
      The angle of the horizontal motor axis.
    surface_plane
      The cut of the analyzer crystal. Either as a tuple (e.g.
      ``(2, 1, 1)`` or a string (e.g. ``"211"``).

    """

    energy_unit = "eV"
    _has_hints: tuple[Device]

    def __init__(
        self,
        *,
        horizontal_motor_prefix: str,
        vertical_motor_prefix: str,
        yaw_motor_prefix: str,
        rowland_diameter: float = 0.5,
        lattice_constant: float = 0.543095,
        wedge_angle: float = 30.0,
        surface_plane: tuple[int, int, int] | str = "211",
        name: str = "",
    ):
        surface_plane_hkl: tuple[int, ...] = tuple(int(i) for i in surface_plane)
        # Create the real motors
        self.horizontal = Motor(horizontal_motor_prefix)
        self.vertical = Motor(vertical_motor_prefix)
        self.crystal_yaw = Motor(yaw_motor_prefix)
        # Reciprocal space geometry
        self.reflection = HKL(initial_value="111")
        self.surface_plane = HKL(initial_value=surface_plane_hkl)
        self.add_readables(
            [
                self.reflection.h,
                self.reflection.k,
                self.reflection.l,
                self.surface_plane.h,
                self.surface_plane.k,
                self.surface_plane.l,
            ],
            StandardReadableFormat.CONFIG_SIGNAL,
        )
        # Soft signals for keeping track of the fixed transform properties
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.rowland_diameter = soft_signal_rw(
                float, units="meter", initial_value=rowland_diameter
            )
            self.wedge_angle = soft_signal_rw(
                float, units="degrees", initial_value=wedge_angle
            )
            self.lattice_constant = soft_signal_rw(
                float, units="nm", initial_value=lattice_constant
            )
            self.bragg_offset = soft_signal_rw(float, units="radians")
            # Soft signals for intermediate, calculated values
            self.d_spacing = derived_signal_r(
                raw_to_derived=self._calc_d_spacing,
                derived_units="nm",
                derived_precision=4,
                H=self.reflection.h,
                K=self.reflection.k,
                L=self.reflection.l,
                a=self.lattice_constant,
            )
            self.asymmetry_angle = derived_signal_r(
                raw_to_derived=self._calc_alpha,
                derived_units="radians",
                H=self.reflection.h,
                K=self.reflection.k,
                L=self.reflection.l,
                h=self.surface_plane.h,
                k=self.surface_plane.k,
                l=self.surface_plane.l,
            )
        # The actual energy signal that controls the analyzer
        self.energy = EnergyPositioner(xtal=self)
        # Decide which signals should be readable/config/etc.
        self.add_readables([self.energy.readback], StandardReadableFormat.HINTED_SIGNAL)
        self.add_readables(
            [
                self.vertical,
                self.horizontal,
            ]
        )
        self.add_readables(
            [
                self.crystal_yaw.user_readback,
            ],
            StandardReadableFormat.CONFIG_SIGNAL,
        )
        super().__init__(name=name)
        # We don't have vertical/horizontal to be hinted, but still configuration
        self._has_hints = tuple(
            device
            for device in self._has_hints
            if device not in [self.vertical, self.horizontal]
        )

    async def connect(
        self,
        mock: bool | LazyMock = False,
        timeout: float = DEFAULT_TIMEOUT,
        force_reconnect: bool = False,
    ) -> None:
        await super().connect(
            mock=mock, timeout=timeout, force_reconnect=force_reconnect
        )
        # Stash units for later. Assumes they won't change
        device_names: list[str] = [
            "horizontal",
            "vertical",
            "crystal_yaw",
            "lattice_constant",
            "rowland_diameter",
            "wedge_angle",
            "asymmetry_angle",
            "d_spacing",
            "energy",
            "bragg_offset",
        ]
        devices = [getattr(self, name) for name in device_names]
        aws = [device_units(device) for device in devices]
        units = await asyncio.gather(*aws)
        self.units = {name: unit for name, unit in zip(device_names, units)}

    def _calc_alpha(self, H: int, K: int, L: int, h: int, k: int, l: int) -> float:
        """Calculate the asymmetry angle for a given reflection and base plane.

        Parameters
        ==========
        H, K, L
          The specific reflection plane to use.
        h, k, l
          The base cut of the crystal surface.

        """
        base = (h, k, l)
        refl = (H, K, L)
        alpha = hkl_to_alpha(base=base, reflection=refl)
        return float(alpha / ureg.radians)

    def _calc_d_spacing(self, H: int, K: int, L: int, a: float) -> float:
        hkl = (H, K, L)
        return float(a / np.linalg.norm(hkl))


class EnergyRaw(TypedDict):
    horizontal: float
    vertical: float


class EnergyDerived(TypedDict):
    energy: float


class EnergyTransform(Transform):
    # To let us get the parent crystal defined on a dynamic subclass
    model_config = ConfigDict(ignored_types=(Analyzer,))

    rowland_diameter: float
    d_spacing: float
    asymmetry_angle: float
    wedge_angle: float

    def derived_to_raw(self, energy: float) -> EnergyRaw:
        """Run a forward (pseudo -> real) calculation"""
        # Apply units
        units = self.xtal.units
        energy = energy * units["energy"]
        D = self.rowland_diameter * units["rowland_diameter"]
        d = self.d_spacing * units["d_spacing"]
        beta = self.wedge_angle * units["wedge_angle"]
        alpha = self.asymmetry_angle * units["asymmetry_angle"]
        # Step 0: convert energy to bragg angle
        bragg = energy_to_bragg(energy, d=d)
        # Step 1: Convert energy params to geometry params
        theta_M = bragg + alpha
        rho = D * np.sin(theta_M)
        # Step 2: Convert geometry params to motor positions
        y = rho * np.cos(theta_M) / np.cos(beta)
        x = -y * np.sin(beta) + rho * np.sin(theta_M)
        # Unroll the units
        x = x.to(units["horizontal"]).magnitude
        y = y.to(units["vertical"]).magnitude
        return EnergyRaw(horizontal=x, vertical=y)

    def raw_to_derived(self, horizontal: float, vertical: float) -> EnergyDerived:
        """Run an inverse (real -> pseudo) calculation"""
        x, y, D, d, beta, alpha = (
            horizontal,
            vertical,
            self.rowland_diameter,
            self.d_spacing,
            self.wedge_angle,
            self.asymmetry_angle,
        )
        log.debug(f"Inverse: {x=}, {y=}, {D=}, {d=}, {beta=}, {alpha=}")
        # Resolve signals into their quantities (with units)
        try:
            units = self.xtal.units
            x = x * units["horizontal"]
            y = y * units["vertical"]
            D = D * units["rowland_diameter"]
            d = d * units["d_spacing"]
            beta = beta * units["wedge_angle"]
            alpha = alpha * units["asymmetry_angle"]
        except (AttributeError, KeyError) as exc:
            log.info(exc)
            return EnergyDerived(energy=float("nan"))
        # Step 1: Convert motor positions to geometry parameters
        theta_M = np.arctan2((x + y * np.sin(beta)), (y * np.cos(beta)))
        log.info(f"Inverse: {theta_M=}")
        rho = y * np.cos(beta) / np.cos(theta_M)
        log.info(f"Inverse: {rho=}")
        # Step 1: Convert geometry params to energy
        bragg = theta_M - alpha
        log.info(f"Inverse: {bragg=}")
        energy = bragg_to_energy(bragg, d=d)
        log.info(f"Inverse: {energy=}")
        energy_val = float(energy.to(units["energy"]).magnitude)
        derived = EnergyDerived(energy=energy_val)
        return derived


class EnergyPositioner(Positioner):
    """Positions the energy of an analyzer crystal."""

    _xtals: dict[str, Analyzer] = {}

    def __init__(self, *, xtal: Analyzer, name: str = ""):
        xtal_signals = {
            "rowland_diameter": xtal.rowland_diameter,
            "d_spacing": xtal.d_spacing,
            "wedge_angle": xtal.wedge_angle,
            "asymmetry_angle": xtal.asymmetry_angle,
        }
        # We need a dynamic class so we can keep access to the xtal units
        this_transform = type("EnergyTransform", (EnergyTransform,), {"xtal": xtal})

        # Need the xtal object in the method, but it can't be a child
        # device of the positioner, but we can't use a partial
        # otherwise we hit this bug maybe(?)
        # https://github.com/python/typing/issues/797
        self._xtals["xtal"] = xtal

        self._setpoint_factory = DerivedSignalFactory(
            this_transform,
            self._set_from_energy,
            horizontal=xtal.horizontal.user_setpoint,
            vertical=xtal.vertical.user_setpoint,
            **xtal_signals,
        )
        self.setpoint = self._setpoint_factory.derived_signal_rw(
            float,
            "energy",
            units="eV",
        )
        self._readback_factory = DerivedSignalFactory(
            this_transform,
            horizontal=xtal.horizontal.user_readback,
            vertical=xtal.vertical.user_readback,
            **xtal_signals,
        )
        with self.add_children_as_readables():
            self.readback = self._readback_factory.derived_signal_r(
                float,
                "energy",
                units="eV",
            )

        # Metadata
        self.velocity, _ = soft_signal_r_and_setter(float, initial_value=0.001)
        self.units, _ = soft_signal_r_and_setter(str, initial_value=xtal.energy_unit)
        self.precision, _ = soft_signal_r_and_setter(int, initial_value=3)
        super().__init__(name=name, put_complete=True)

    async def _set_from_energy(self, value: float):
        transform = await self._setpoint_factory.transform()
        raw = transform.derived_to_raw(energy=value)
        # Set the new calculated signals
        xtal = self._xtals["xtal"]
        await asyncio.gather(
            xtal.horizontal.set(raw["horizontal"]),
            xtal.vertical.set(raw["vertical"]),
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
