import asyncio
import logging

from scipy import constants
import numpy as np
from ophyd import Component as Cpt
from ophyd import Device, EpicsMotor
from ophyd import FormattedComponent as FCpt
from ophyd import PseudoPositioner, PseudoSingle, Signal
from ophyd.pseudopos import pseudo_position_argument, real_position_argument
from ophyd_async.core import Device, soft_signal_rw, soft_signal_r_and_setter
from scipy import constants

from .motor import Motor
from ..positioner import Positioner
from .signal import derived_signal_r, derived_signal_rw

log = logging.getLogger(__name__)

um_per_mm = 1000


h = constants.physical_constants["Planck constant in eV/Hz"][0]
c = constants.c


def energy_to_wavelength(energy):
    """Energy in eV to wavelength in meters."""
    return h * c / energy


wavelength_to_energy = energy_to_wavelength


def bragg_to_wavelength(bragg_angle: float, d: float, n: int = 1):
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


def wavelength_to_bragg(wavelength: float, d: float, n: int = 1):
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


def energy_to_bragg(energy: float, d: float) -> float:
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


def bragg_to_energy(bragg: float, d: float) -> float:
    """Convert Bragg angle to photon energy.

    Parameters
    ==========
    bragg
      Bragg angle for the crystal, in radians.
    d
      d-spacing of the analyzer crystal, in meters.

    Returns
    =======
    energy
      Photon energy, in eV.

    """
    energy = h * c / 2 / d / np.sin(bragg)
    return energy


class Analyzer(Device):
    """A pseudo positioner describing a rowland circle.

    Real Axes
    =========
    x
    y
    z
    z1

    Pseudo Axes
    ===========
    D
      In mm
    theta
      In degrees
    alpha
      In degrees
    """

    def __init__(
        self,
        *,
        x_motor_prefix: str,
        z_motor_prefix: str,
        name: str = "",
    ):
        # Create the real motors
        self.x = Motor(x_motor_prefix)
        self.z = Motor(z_motor_prefix)
        # Soft signals for keeping track of the fixed transform properties
        self.d_spacing = soft_signal_rw(float, units="Å", precision=4)
        self.rowland_diameter = soft_signal_rw(float, units="mm")
        self.wedge_angle = soft_signal_rw(float, units="rad")
        self.alpha = soft_signal_rw(float, units="rad")
        # The actual energy signal that controls the analyzer
        self.energy = EnergyPositioner(xtal=self)
        super().__init__(name=name)


class EnergyPositioner(Positioner):
    """Positions the energy of an analyzer crystal."""
    put_complete = True

    def __init__(self, *, xtal: Analyzer, name: str = ""):
        xtal_signals = {
            "D": xtal.rowland_diameter,
            "d": xtal.d_spacing,
            "beta": xtal.wedge_angle,
            "alpha": xtal.alpha,
            # "x": xtal.x,
            # "z": xtal.z,
        }
        self.setpoint = derived_signal_rw(
            float,
            units="eV",
            derived_from=dict(
                x=xtal.x.user_setpoint, z=xtal.z.user_setpoint, **xtal_signals
            ),
            forward=self.forward,
            inverse=self.inverse,
        )
        self.readback = derived_signal_r(
            float,
            units="eV",
            derived_from=dict(
                x=xtal.x.user_readback, z=xtal.z.user_readback, **xtal_signals
            ),
            inverse=self.inverse,
        )
        # Metadata
        self.velocity, _ = soft_signal_r_and_setter(float, initial_value=1)
        self.units, _ = soft_signal_r_and_setter(str, initial_value="eV")
        self.precision, _ = soft_signal_r_and_setter(int, initial_value=3)

    async def forward(self, value, D, d, beta, alpha, x, z):
        """Run a forward (pseudo -> real) calculation"""
        # Resolve the dependent signals into their values
        energy = value
        D, d, beta, alpha = await asyncio.gather(
            D.get_value(),
            d.get_value(),
            beta.get_value(),
            alpha.get_value(),
        )
        # Step 0: convert energy to bragg angle
        bragg = energy_to_bragg(energy, d=d)
        # Step 1: Convert energy params to geometry params
        theta_M = bragg + alpha
        rho = D * np.sin(theta_M)
        # Step 2: Convert geometry params to motor positions
        z_val = rho * np.cos(theta_M) / np.cos(beta)
        x_val = -z_val * np.sin(beta) + rho * np.sin(theta_M)
        # Report the calculated result
        return {
            x: x_val,
            z: z_val,
        }

    def inverse(self, values, D, d, beta, alpha, x, z):
        """Run an inverse (real -> pseudo) calculation"""
        # Resolve signals into their values
        x = values[x]
        z = values[z]
        D = values[D]
        d = values[d]
        beta = values[beta]
        alpha = values[alpha]
        # Step 1: Convert motor positions to geometry parameters
        theta_M = np.arctan2((x + z * np.sin(beta)), (z * np.cos(beta)))
        rho = z * np.cos(beta) / np.cos(theta_M)
        # Step 1: Convert geometry params to energy
        bragg = theta_M - alpha
        energy = bragg_to_energy(bragg, d=d)
        return energy


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
