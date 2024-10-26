import math
import time

import numpy as np
import pytest
from ophyd.sim import make_fake_device
from ophyd_async.core import get_mock_put, set_mock_value

from haven.devices import analyzer

um_per_mm = 1000


energy_to_wavelength_values = [
    # (eV,      meters)
    (61992.35, 0.2e-10),
    (24796.94, 0.5e-10),
    (12398.47, 1.0e-10),
    (8041.555, 1.5418e-10),
    (6199.235, 2.00e-10),
    (2000.0, 6.19924e-10),
]


@pytest.mark.parametrize("energy, wavelength", energy_to_wavelength_values)
def test_energy_to_wavelength(energy, wavelength):
    assert pytest.approx(analyzer.energy_to_wavelength(energy)) == wavelength


@pytest.mark.parametrize("energy, wavelength", energy_to_wavelength_values)
def test_wavelength_to_energy(energy, wavelength):
    assert pytest.approx(analyzer.wavelength_to_energy(wavelength), rel=0.001) == energy


braggs_law_values = [
    # (θ°,   d(Å), λ(Å))
    (35.424, 1.33, 1.5418),
    (48.75,  1.33, 2.0),
    (75,     1.33, 2.5694),
    (50.43,  1.0,  1.5418),
    (22.67,  2.0,  1.5418),
]


@pytest.mark.parametrize("theta, d_spacing, wavelength", braggs_law_values)
def test_bragg_to_wavelength(theta, d_spacing, wavelength):
    theta = np.radians(theta)
    d_spacing *= 1e-10
    wavelength *= 1e-10
    assert pytest.approx(analyzer.bragg_to_wavelength(theta, d=d_spacing)) == wavelength


@pytest.mark.parametrize("theta, d_spacing, wavelength", braggs_law_values)
def test_wavelength_to_bragg(theta, d_spacing, wavelength):
    theta = np.radians(theta)
    d_spacing *= 1e-10
    wavelength *= 1e-10
    assert (
        pytest.approx(analyzer.wavelength_to_bragg(wavelength, d=d_spacing), rel=0.001)
        == theta
    )


analyzer_values = [
    # (θB,    α,     β,    y,      x)
    (70,      15,    25,   4.79,   47.60),
    (80,      7,     10,   2.65,   49.40),
    (60,      20,    30,   9.87,   43.56),
    (65,      0,     0,    19.15,  41.07),
    (80,      30,    10,   -16.32, 46.98),
]


@pytest.fixture()
async def xtal(sim_registry):
    # Create the analyzer documents
    xtal = analyzer.Analyzer(name="analyzer", horizontal_motor_prefix="", vertical_motor_prefix="", yaw_motor_prefix="", surface_plane=(0, 0, 1))
    await xtal.connect(mock=True)
    # Set default values for xtal parameters
    d = 1.637 * 1e-10  # Si 311 converted to meters
    set_mock_value(xtal.d_spacing, d)
    set_mock_value(xtal.rowland_diameter, 0.500)
    return xtal


@pytest.mark.parametrize("bragg,alpha,beta,y,x", analyzer_values)
async def test_rowland_circle_forward(xtal, bragg, alpha, beta, x, y):
    # Set up sensible values for current positions
    set_mock_value(xtal.wedge_angle, np.radians(beta))
    set_mock_value(xtal.asymmetry_angle, np.radians(alpha))
    set_mock_value(xtal.horizontal.user_readback, 0)
    set_mock_value(xtal.vertical.user_readback, 0)
    d = await xtal.d_spacing.get_value()
    bragg = np.radians(bragg)
    energy = analyzer.bragg_to_energy(bragg, d=d)
    # Check the result is correct (convert cm -> m)
    expected = (x / 100, y / 100)
    await xtal.energy.set(energy)
    x_mock = get_mock_put(xtal.horizontal.user_setpoint)
    x_mock.assert_called_once()
    assert x_mock.call_args.args[0] == pytest.approx(x/100, abs=0.0001)
    y_mock = get_mock_put(xtal.vertical.user_setpoint)
    y_mock.assert_called_once()
    assert y_mock.call_args.args[0] == pytest.approx(y/100, abs=0.0001)


@pytest.mark.parametrize("bragg,alpha,beta,y,x", analyzer_values)
async def test_rowland_circle_inverse(xtal, bragg, alpha, beta, x, y):
    set_mock_value(xtal.wedge_angle, np.radians(beta))
    set_mock_value(xtal.asymmetry_angle, np.radians(alpha))
    # Calculate the expected answer
    bragg = np.radians(bragg)
    d = await xtal.d_spacing.get_value()
    expected_energy = analyzer.bragg_to_energy(bragg, d=d)
    # Compare to the calculated inverse
    set_mock_value(xtal.horizontal.user_readback, x)
    set_mock_value(xtal.vertical.user_readback, y)
    new_energy = await xtal.energy.readback.get_value()
    assert new_energy == pytest.approx(expected_energy, abs=0.2)


reflection_values = [
    # (cut, refl,  α°   )
    ("001", "101", 45.0),
    ("001", "110", 90.0),
    ("211", "444", 19.5),
    ("211", "733",  4.0),
    ("211", "880", 30.0),
]


@pytest.mark.parametrize("cut,refl,alpha", reflection_values)
async def test_asymmetry_angle(xtal, cut, refl, alpha):
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
