import asyncio
import math
from unittest.mock import AsyncMock

import pytest
from ophyd_async.core import soft_signal_rw
from ophyd_async.testing import set_mock_value

from haven.devices.asymmotron import (
    Analyzer,
    Motor,
    bragg_to_energy,
    bragg_to_wavelength,
    device_units,
    energy_to_wavelength,
    ureg,
    wavelength_to_bragg,
    wavelength_to_energy,
)

energy_to_wavelength_values = [
    # (eV,      meters)
    (61992.35, 0.2e-10),
    (24796.94, 0.5e-10),
    (12398.47, 1.0e-10),
    (8041.555, 1.5418e-10),
    (6199.235, 2.00e-10),
    (2000.0, 6.19924e-10),
]


async def test_motor_units():
    motor = Motor("")
    await motor.connect(mock=True)
    set_mock_value(motor.motor_egu, "μm")
    assert await device_units(motor) == ureg.um


async def test_signal_units():
    signal = soft_signal_rw(float, units="nm")
    await signal.connect(mock=True)
    assert await device_units(signal) == ureg.nm


@pytest.mark.parametrize("energy, wavelength", energy_to_wavelength_values)
def test_energy_to_wavelength(energy: float, wavelength: float):
    new_wavelength = energy_to_wavelength(energy * ureg.eV).to(ureg.meter).magnitude
    assert pytest.approx(new_wavelength) == wavelength


@pytest.mark.parametrize("energy, wavelength", energy_to_wavelength_values)
def test_wavelength_to_energy(energy, wavelength):
    new_energy = wavelength_to_energy(wavelength * ureg.m).to(ureg.eV).magnitude
    assert pytest.approx(new_energy, rel=0.001) == energy


braggs_law_values = [
    # (θ°,   d(Å), λ(Å))
    (35.424, 1.33, 1.5418),
    (48.75, 1.33, 2.0),
    (75, 1.33, 2.5694),
    (50.43, 1.0, 1.5418),
    (22.67, 2.0, 1.5418),
]


@pytest.mark.parametrize("theta, d_spacing, wavelength", braggs_law_values)
def test_bragg_to_wavelength(theta, d_spacing, wavelength):
    theta = theta * ureg.degrees
    d_spacing *= ureg.angstrom
    wavelength *= ureg.angstrom
    assert (
        pytest.approx(bragg_to_wavelength(theta, d=d_spacing), rel=0.0001) == wavelength
    )


@pytest.mark.parametrize("theta, d_spacing, wavelength", braggs_law_values)
def test_wavelength_to_bragg(theta, d_spacing, wavelength):
    d_spacing *= ureg.angstrom
    wavelength *= ureg.angstrom
    new_bragg = wavelength_to_bragg(wavelength, d=d_spacing).to(ureg.degrees).magnitude
    assert new_bragg == pytest.approx(theta, rel=0.001)


analyzer_values = [
    # (θB,  α,  β,      y,     x)
    (70, 15, 25, 4.79, 47.60),
    (80, 7, 10, 2.65, 49.40),
    (60, 20, 30, 9.87, 43.56),
    (65, 0, 0, 19.15, 41.07),
    (80, 30, 10, -16.32, 46.98),
]


Si311_d_spacing = 0.1637  # in nm


@pytest.fixture()
async def xtal(sim_registry):
    # Create the analyzer documents
    xtal = Analyzer(
        name="analyzer",
        horizontal_motor_prefix="",
        vertical_motor_prefix="",
        yaw_motor_prefix="",
        surface_plane=(0, 0, 1),
    )
    await xtal.connect(mock=True)
    # Set default values for xtal parameters
    set_mock_value(xtal.d_spacing, Si311_d_spacing)
    set_mock_value(xtal.rowland_diameter, 500)
    xtal.units[xtal.horizontal] = ureg.cm
    xtal.units[xtal.vertical] = ureg.cm
    xtal.units[xtal.rowland_diameter] = ureg.mm
    xtal.units[xtal.d_spacing] = ureg.nm
    xtal.units[xtal.wedge_angle] = ureg.degrees
    xtal.units[xtal.asymmetry_angle] = ureg.degrees
    return xtal


async def test_set_hkl(xtal):
    await xtal.reflection.set("137")
    hkl = await asyncio.gather(
        xtal.reflection.h.get_value(),
        xtal.reflection.k.get_value(),
        xtal.reflection.l.get_value(),
    )
    assert tuple(hkl) == (1, 3, 7)


@pytest.mark.parametrize("bragg,alpha,beta,y,x", analyzer_values)
async def test_rowland_circle_forward(xtal, bragg, alpha, beta, x, y):
    # Set up sensible values for current positions
    xtal.wedge_angle.get_value = AsyncMock(return_value=beta)
    xtal.asymmetry_angle.get_value = AsyncMock(return_value=alpha)
    xtal.d_spacing.get_value = AsyncMock(return_value=Si311_d_spacing)
    energy = bragg_to_energy(bragg * ureg.degrees, d=Si311_d_spacing * ureg.nm)
    # Calculate the new x, z motor positions
    calculated = await xtal.energy.forward(
        energy.to(ureg.electron_volt).magnitude,
        D=xtal.rowland_diameter,
        d=xtal.d_spacing,
        beta=xtal.wedge_angle,
        alpha=xtal.asymmetry_angle,
        x=xtal.horizontal,
        y=xtal.vertical,
    )
    # Check the result is correct (convert cm -> m)
    expected = {xtal.horizontal: x, xtal.vertical: y}
    assert calculated[xtal.horizontal] == pytest.approx(x, abs=0.1)
    assert calculated[xtal.vertical] == pytest.approx(y, abs=0.1)


@pytest.mark.parametrize("bragg,alpha,beta,y,x", analyzer_values)
async def test_rowland_circle_inverse(xtal, bragg, alpha, beta, x, y):
    # Calculate the new energy
    D = await xtal.rowland_diameter.get_value()
    new_energy = xtal.energy.inverse(
        {
            xtal.horizontal: x,
            xtal.vertical: y,
            xtal.rowland_diameter: D,
            xtal.d_spacing: Si311_d_spacing,
            xtal.wedge_angle: beta,
            xtal.asymmetry_angle: alpha,
        },
        D=xtal.rowland_diameter,
        d=xtal.d_spacing,
        beta=xtal.wedge_angle,
        alpha=xtal.asymmetry_angle,
        x=xtal.horizontal,
        y=xtal.vertical,
    )
    # Compare to the calculated inverse
    expected_energy = bragg_to_energy(bragg * ureg.degrees, d=Si311_d_spacing * ureg.nm)
    expected_energy = expected_energy.to(ureg.electron_volt).magnitude
    assert new_energy == pytest.approx(expected_energy, abs=0.2)


reflection_values = [
    # (cut, refl,  α°   )
    ("001", "101", 45.0),
    ("001", "110", 90.0),
    ("211", "444", 19.5),
    ("211", "733", 4.0),
    ("211", "880", 30.0),
]


@pytest.mark.parametrize("cut,refl,alpha", reflection_values)
async def test_asymmetry_angle(xtal, cut, refl, alpha):
    await xtal.asymmetry_angle.connect(mock=False)
    cut = tuple(int(i) for i in cut)
    refl = tuple(int(i) for i in refl)
    alpha = math.radians(alpha)
    await xtal.reflection.set(refl)
    await xtal.surface_plane.set(cut)
    # Compare to the calculated inverse
    new_alpha = await xtal.asymmetry_angle.get_value()
    assert new_alpha == pytest.approx(alpha, abs=0.02)


d_spacing_values = [
    # Assuming a = 5.4311959Å
    # https://www.globalsino.com/EM/page4489.html
    # (hkl, d)
    ("111", 3.135),
    ("220", 1.920),
    ("511", 1.045),
    ("622", 0.819),
]


@pytest.mark.parametrize("hkl,d", d_spacing_values)
async def test_d_spacing(xtal, hkl, d):
    await xtal.d_spacing.connect(mock=False)
    await xtal.lattice_constant.set(5.4311959)
    hkl = tuple(int(h) for h in hkl)  # str to tuple
    await xtal.reflection.set(hkl)
    assert await xtal.d_spacing.get_value() == pytest.approx(d, abs=0.001)


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
