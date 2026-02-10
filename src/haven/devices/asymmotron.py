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
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    Array1D,
    DerivedSignalFactory,
    Device,
    LazyMock,
    SignalR,
    StandardReadable,
    StandardReadableFormat,
    Transform,
    derived_signal_r,
    soft_signal_r_and_setter,
)
from ophyd_async.epics.core import epics_signal_rw
from pint import Quantity
from pydantic import ConfigDict

from haven.devices.motor import Motor
from haven.positioner import Positioner
from haven.units import (
    bragg_to_energy,
    energy_to_bragg,
    ureg,
)

__all__ = ["Analyzer"]

log = logging.getLogger(__name__)


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


def hkl_to_alpha(base, reflection) -> Quantity:
    cos_alpha = (
        np.dot(base, reflection) / np.linalg.norm(base) / np.linalg.norm(reflection)
    )
    if cos_alpha > 1:
        cos_alpha = 1
    alpha = np.arccos(cos_alpha) * ureg.radians
    return alpha


class Analyzer(StandardReadable):
    """A single asymmetric analyzer crystal mounted on an Rowland circle.

    **Units** are handled automatically based on units set in EPICS
    PVs.

    Parameters
    ==========
    prefix
      The IOC prefix for analyzer state PVs. E.g. "25idc:asymm0:"
    chord_motor_prefix
      The PV prefix for the motor moving the crystal inboard/outboard.
    pitch_motor_prefix
      The PV prefix for the motor moving the crystal angle relative to
      the incoming beam.
    yaw_motor_prefix
      The PV prefix for the motor rotating the crystal around its
      optical axis.

    """

    energy_unit = "eV"
    _has_hints: tuple[Device]

    def __init__(
        self,
        *,
        prefix: str,
        chord_motor_prefix: str,
        pitch_motor_prefix: str,
        yaw_motor_prefix: str,
        name: str = "",
    ):
        # Create the real motors
        self.chord = Motor(chord_motor_prefix)
        self.crystal_pitch = Motor(pitch_motor_prefix)
        self.crystal_yaw = Motor(yaw_motor_prefix)
        # Reciprocal space geometry
        self.reflection = epics_signal_rw(Array1D[np.uint8], f"{prefix}reflection")
        self.surface_plane = epics_signal_rw(Array1D[np.uint8], f"{prefix}surfacePlane")
        self.add_readables(
            [
                self.reflection,
                self.surface_plane,
            ],
            StandardReadableFormat.CONFIG_SIGNAL,
        )
        # Soft signals for keeping track of the fixed transform properties
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.rowland_diameter = epics_signal_rw(float, f"{prefix}diameter")
            self.lattice_constant = epics_signal_rw(float, f"{prefix}latticeConstant")
            self.bragg_offset = epics_signal_rw(float, f"{prefix}braggOffset")
            # Soft signals for intermediate, calculated values
            self.d_spacing = derived_signal_r(
                raw_to_derived=self._calc_d_spacing,
                derived_units="nm",
                derived_precision=4,
                HKL=self.reflection,
                a=self.lattice_constant,
            )
            self.asymmetry_angle = derived_signal_r(
                raw_to_derived=self._calc_alpha,
                derived_units="radians",
                HKL=self.reflection,
                hkl=self.surface_plane,
            )
        # The actual energy signal that controls the analyzer
        self.energy = EnergyPositioner(xtal=self)
        # Decide which signals should be readable/config/etc.
        self.add_readables([self.energy.readback], StandardReadableFormat.HINTED_SIGNAL)
        self.add_readables(
            [
                self.crystal_pitch,
                self.chord,
            ]
        )
        self.add_readables(
            [
                self.crystal_yaw.user_readback,
            ],
            StandardReadableFormat.CONFIG_SIGNAL,
        )
        super().__init__(name=name)
        # We don't have pitch/chord to be hinted, but still configuration
        self._has_hints = tuple(
            device
            for device in self._has_hints
            if device not in [self.crystal_pitch, self.chord]
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
            "chord",
            "crystal_pitch",
            "crystal_yaw",
            "lattice_constant",
            "rowland_diameter",
            # "asymmetry_angle",
            # "d_spacing",
            # "energy",
            "bragg_offset",
        ]
        devices = [getattr(self, name) for name in device_names]
        aws = [device_units(device) for device in devices]
        units = await asyncio.gather(*aws)
        self.units = {name: unit for name, unit in zip(device_names, units)}

    def _calc_alpha(
        self, HKL: tuple[int, int, int], hkl: tuple[int, int, int]
    ) -> float:
        """Calculate the asymmetry angle for a given reflection and base plane.

        Parameters
        ==========
        H, K, L
          The specific reflection plane to use.
        h, k, l
          The base cut of the crystal surface.

        """
        alpha = hkl_to_alpha(base=hkl, reflection=HKL)
        return float(alpha / ureg.radians)

    def _calc_d_spacing(self, HKL: tuple[int, int, int], a: float) -> float:
        return float(a / np.linalg.norm(HKL))


class EnergyRaw(TypedDict):
    chord: float
    crystal_pitch: float


class EnergyDerived(TypedDict):
    energy: float


def _derived_units(signal):
    """Get the Pint units for a derived signal."""
    return ureg(signal._connector.backend.metadata["units"])


class EnergyTransform(Transform):
    # To let us get the parent crystal defined on a dynamic subclass
    model_config = ConfigDict(ignored_types=(Analyzer,))

    rowland_diameter: float
    d_spacing: float
    asymmetry_angle: float

    def derived_to_raw(self, energy: float) -> EnergyRaw:
        """Run a forward (pseudo -> real) calculation"""
        # Apply units
        units = self.xtal.units
        energy = energy * ureg(self.xtal.energy_unit)
        D = self.rowland_diameter * units["rowland_diameter"]
        d = self.d_spacing * _derived_units(self.xtal.d_spacing)
        alpha = self.asymmetry_angle * _derived_units(self.xtal.asymmetry_angle)
        # Step 0: convert energy to bragg angle
        bragg = energy_to_bragg(energy, d=d)
        print(f"{bragg=}, {alpha=}")
        # Convert energy params to geometry params
        theta_M = bragg + alpha
        rho = D * np.sin(theta_M)
        print(theta_M, rho)
        raw = EnergyRaw(
            chord=float(rho.to(units["chord"]).magnitude),
            crystal_pitch=float(theta_M.to(units["crystal_pitch"]).magnitude),
        )
        return raw

    def raw_to_derived(self, chord: float, crystal_pitch: float) -> EnergyDerived:
        """Run an inverse (real -> pseudo) calculation"""
        rho, theta_M, D, d, alpha = (
            chord,
            crystal_pitch,
            self.rowland_diameter,
            self.d_spacing,
            self.asymmetry_angle,
        )
        log.debug(f"Inverse: θM={theta_M}, ρ={rho}, {D=}, {d=}, {alpha=}")
        # Resolve signals into their quantities (with units)
        try:
            units = self.xtal.units
            rho = rho * units["chord"]
            theta_M = theta_M * units["crystal_pitch"]
            D = D * units["rowland_diameter"]
            d = d * _derived_units(self.xtal.d_spacing)
            alpha = alpha * _derived_units(self.xtal.asymmetry_angle)
        except (AttributeError, KeyError) as exc:
            log.info(exc)
            return EnergyDerived(energy=float("nan"))
        # Convert geometry params to energy
        bragg = theta_M - alpha
        log.debug(f"Inverse: {bragg=}")
        energy = bragg_to_energy(bragg, d=d)
        log.debug(f"Inverse: {energy=}")
        energy_val = float(energy.to(ureg(self.xtal.energy_unit)).magnitude)
        derived = EnergyDerived(energy=energy_val)
        return derived


class EnergyPositioner(Positioner):
    """Positions the energy of an analyzer crystal."""

    _xtals: dict[str, Analyzer] = {}

    def __init__(self, *, xtal: Analyzer, name: str = ""):
        xtal_signals = {
            "rowland_diameter": xtal.rowland_diameter,
            "d_spacing": xtal.d_spacing,
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
            chord=xtal.chord.user_setpoint,
            crystal_pitch=xtal.crystal_pitch.user_setpoint,
            **xtal_signals,
        )
        self.setpoint = self._setpoint_factory.derived_signal_rw(
            float,
            "energy",
            units="eV",
        )
        self._readback_factory = DerivedSignalFactory(
            this_transform,
            chord=xtal.chord.user_readback,
            crystal_pitch=xtal.crystal_pitch.user_readback,
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
            xtal.chord.set(raw["chord"]),
            xtal.crystal_pitch.set(raw["crystal_pitch"]),
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
