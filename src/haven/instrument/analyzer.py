import asyncio
import logging

from scipy import constants
import numpy as np
from ophyd import Component as Cpt
from ophyd import Device, EpicsMotor
from ophyd import FormattedComponent as FCpt
from ophyd import PseudoPositioner, PseudoSingle, Signal
from ophyd.pseudopos import pseudo_position_argument, real_position_argument
from scipy import constants

from .._iconfig import load_config
from .device import aload_devices, make_device

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

    # Pseudo axes
    energy: PseudoSingle = Cpt(PseudoSingle, name="energy", limits=(0, 1000))
    alpha: PseudoSingle = Cpt(PseudoSingle, name="alpha", limits=(0, 180))

    # Real axes
    x: EpicsMotor = FCpt(EpicsMotor, "{x_motor_pv}", name="x")
    z: EpicsMotor = FCpt(EpicsMotor, "{z_motor_pv}", name="z")

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        """Run a forward (pseudo -> real) calculation"""
        # Convert distance to microns and degrees to radians
        energy, alpha = pseudo_pos.energy, pseudo_pos.alpha
        # Step 0: convert energy to bragg angle
        bragg = energy_to_bragg(energy, d=self.d_spacing.get())
        # Step 1: Convert energy params to geometry params
        D = self.rowland_diameter.get(use_monitor=True)
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
        theta_M = np.arctan((x + z * np.sin(beta)) / (z * np.cos(beta)))
        rho = z * np.cos(beta) / np.cos(theta_M)
        print(f"{x=}, {z=}, {beta=}, {theta_M=}, {rho}")
        return self.PseudoPosition(energy=0, alpha=0)


# Rewrite the following four equations so that they calculate D, theta and alpha based on inputting x, y, z1 and z.

#         x = D * (sin(theta + alpha)) ** 2
#         y = D * ((sin(theta + alpha)) ** 2 - (sin(theta - alpha)) ** 2)
#         z1 = D * sin(theta - alpha) * cos(theta + alpha)
#         z = z1 + D * sin(theta - alpha) * cos(theta - alpha)

# To calculate D, theta, and alpha based on x, y, z1, and z, we can rearrange the given equations as follows:

# D = x / (sin(theta + alpha)) ** 2

# sin(theta - alpha) = z1 / (D * cos(theta + alpha))

# cos(theta - alpha) = (z - z1) / (D * sin(theta - alpha))

# Substitute the above two equations into the expression for y:

# y = D * ((sin(theta + alpha)) ** 2 - (sin(theta - alpha)) ** 2)

# y = D * ((sin(theta + alpha)) ** 2 - (z1 / (D * cos(theta + alpha))) ** 2)

# y = D * ((sin(theta + alpha)) ** 2 - (z1 ** 2 / D ** 2) * (cos(theta + alpha)) ** (-2))

# Solve for cos(theta + alpha) in the above equation:

# cos(theta + alpha) = (z1 ** 2 / (D ** 2 * y + z1 ** 2)) ** 0.5

# Substitute the value of cos(theta + alpha) into the equation for sin(theta - alpha):

# sin(theta - alpha) = z1 / (D * (z1 ** 2 / (D ** 2 * y + z1 ** 2)) ** 0.5)

# Simplify the above equation:

# sin(theta - alpha) = (z1 ** 2 / (D ** 2 * y + z1 ** 2)) ** 0.5

# Finally, substitute the values of cos(theta + alpha) and sin(theta - alpha) into the equation for D:

# D = x / ((sin(theta + alpha)) ** 2)

# D = x / ((1 - (z1 ** 2 / (D ** 2 * y + z1 ** 2))) ** 2)

# This equation can be solved numerically to obtain the value of D. Once D is known, we can use the equations for cos(theta + alpha) and sin(theta - alpha) to calculate theta and alpha.


# class LERIXSpectrometer(Device):
#     rowland = Cpt(
#         RowlandPositioner,
#         x_motor_pv="vme_crate_ioc:m1",
#         y_motor_pv="vme_crate_ioc:m2",
#         z_motor_pv="vme_crate_ioc:m3",
#         z1_motor_pv="vme_crate_ioc:m4",
#         name="rowland",
#     )


# async def make_lerix_device(name: str, x_pv: str, y_pv: str, z_pv: str, z1_pv: str):
#     dev = RowlandPositioner(
#         name=name,
#         x_motor_pv=x_pv,
#         y_motor_pv=y_pv,
#         z_motor_pv=z_pv,
#         z1_motor_pv=z1_pv,
#         labels={"lerix_spectrometers"},
#     )
#     pvs = ", ".join((x_pv, y_pv, z_pv, z1_pv))
#     try:
#         await await_for_connection(dev)
#     except TimeoutError as exc:
#         log.warning(f"Could not connect to LERIX spectrometer: {name} ({pvs})")
#     else:
#         log.info(f"Created area detector: {name} ({pvs})")
#         return dev


def load_lerix_spectrometer_coros(config=None):
    """Create co-routines for creating/connecting the LERIX spectrometer
    devices.

    """
    if config is None:
        config = load_config()
    # Create spectrometers
    for name, cfg in config.get("lerix", {}).items():
        rowland = cfg["rowland"]
        yield make_device(
            RowlandPositioner,
            name=name,
            x_motor_pv=rowland["x_motor_pv"],
            y_motor_pv=rowland["y_motor_pv"],
            z_motor_pv=rowland["z_motor_pv"],
            z1_motor_pv=rowland["z1_motor_pv"],
            labels={"lerix_spectromoters"},
        )


def load_lerix_spectrometers(config=None):
    asyncio.run(aload_devices(*load_lerix_spectrometer_coros(config=config)))


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
