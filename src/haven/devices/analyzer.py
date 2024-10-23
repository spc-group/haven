import logging

from scipy import constants
import numpy as np
from ophyd import Component as Cpt
from ophyd import Device, EpicsMotor
from ophyd import FormattedComponent as FCpt
from ophyd import PseudoPositioner, PseudoSingle, Signal
from ophyd.pseudopos import pseudo_position_argument, real_position_argument
from scipy import constants

log = logging.getLogger(__name__)

um_per_mm = 1000


h = constants.physical_constants['Planck constant in eV/Hz'][0]
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


class Analyzer(PseudoPositioner):
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
        x_motor_pv: str,
        z_motor_pv: str,
        *args,
        **kwargs,
    ):
        self.x_motor_pv = x_motor_pv
        self.z_motor_pv = z_motor_pv
        super().__init__(*args, **kwargs)

    # Other signals
    d_spacing: Signal = Cpt(Signal, name="d_spacing")  # In Å
    rowland_diameter: Signal = Cpt(Signal, name="rowland_diameter")  # In mm
    wedge_angle: Signal = Cpt(Signal, name="wedge_angle")  # In radians
    alpha: Signal = Cpt(Signal, name="alpha")

    # Pseudo axes
    energy: PseudoSingle = Cpt(PseudoSingle, name="energy", limits=(0, 1000))

    # Real axes
    x: EpicsMotor = FCpt(EpicsMotor, "{x_motor_pv}", name="x")
    z: EpicsMotor = FCpt(EpicsMotor, "{z_motor_pv}", name="z")

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        """Run a forward (pseudo -> real) calculation"""
        # Convert distance to microns and degrees to radians
        energy = pseudo_pos.energy
        # Step 0: convert energy to bragg angle
        bragg = energy_to_bragg(energy, d=self.d_spacing.get())
        # Step 1: Convert energy params to geometry params
        D = self.rowland_diameter.get(use_monitor=True)
        alpha = self.alpha.get()
        theta_M = bragg + alpha
        rho = D * np.sin(theta_M)
        # Step 2: Convert geometry params to motor positions
        beta = self.wedge_angle.get(use_monitor=True)
        z = rho * np.cos(theta_M) / np.cos(beta)
        x = -z * np.sin(beta) + rho * np.sin(theta_M)
        # Report the calculated result
        return self.RealPosition(
            x=x,
            z=z,
        )

    @real_position_argument
    def inverse(self, real_pos):
        """Run an inverse (real -> pseudo) calculation"""
        beta = self.wedge_angle.get(use_monitor=True)
        x = real_pos.x
        z = real_pos.z
        # Step 1: Convert motor positions to geometry parameters
        theta_M = np.arctan2((x + z * np.sin(beta)) , (z * np.cos(beta)))
        rho = z * np.cos(beta) / np.cos(theta_M)
        alpha = self.alpha.get()
        bragg = theta_M - alpha
        print(f"{x=}, {z=}, {beta=}, {theta_M=}, {rho=}, {bragg=}, {alpha=}")
        energy = bragg_to_energy(bragg, d=self.d_spacing.get())
        return self.PseudoPosition(energy=energy)


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
