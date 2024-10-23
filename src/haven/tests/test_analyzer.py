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
    # (bragg, alpha, beta, z,      x)
    (70,      15,    25,   4.79,  47.60),
    (80,      7,     10,   2.65,   49.40),
    (60,      20,    30,   9.87,   43.56),
    (65,      0,     0,   19.15,  41.07),
    (80,      30,    10,  -16.32, 46.98),
]


@pytest.fixture()
async def xtal(sim_registry):
    # Create the analyzer documents
    xtal = analyzer.Analyzer(name="analyzer", x_motor_prefix="", z_motor_prefix="")
    await xtal.connect(mock=True)
    # Set default values for xtal parameters
    d = 1.637 * 1e-10  # Si 311 converted to meters
    await xtal.d_spacing.set(d)
    await xtal.rowland_diameter.set(0.500)
    return xtal


@pytest.mark.parametrize("bragg,alpha,beta,z,x", analyzer_values)
async def test_rowland_circle_forward(xtal, bragg, alpha, beta, x, z):
    # Set up sensible values for current positions
    set_mock_value(xtal.wedge_angle, np.radians(beta))
    set_mock_value(xtal.alpha, np.radians(alpha))
    set_mock_value(xtal.x.user_readback, 0)
    set_mock_value(xtal.z.user_readback, 0)
    d = await xtal.d_spacing.get_value()
    bragg = np.radians(bragg)
    energy = analyzer.bragg_to_energy(bragg, d=d)
    # Check the result is correct (convert cm -> m)
    expected = (x / 100, z / 100)
    await xtal.energy.set(energy)
    x_mock = get_mock_put(xtal.x.user_setpoint)
    x_mock.assert_called_once()
    assert x_mock.call_args.args[0] == pytest.approx(x/100, abs=0.0001)
    z_mock = get_mock_put(xtal.z.user_setpoint)
    z_mock.assert_called_once()
    assert z_mock.call_args.args[0] == pytest.approx(z/100, abs=0.0001)


@pytest.mark.parametrize("bragg,alpha,beta,z,x", analyzer_values)
async def test_rowland_circle_inverse(xtal, bragg, alpha, beta, x, z):
    set_mock_value(xtal.wedge_angle, np.radians(beta))
    set_mock_value(xtal.alpha, np.radians(alpha))
    # Calculate the expected answer
    bragg = np.radians(bragg)
    d = await xtal.d_spacing.get_value()
    expected_energy = analyzer.bragg_to_energy(bragg, d=d)
    # Compare to the calculated inverse
    set_mock_value(xtal.x.user_readback, x)
    set_mock_value(xtal.z.user_readback, z)
    new_energy = await xtal.energy.readback.get_value()
    assert new_energy == pytest.approx(expected_energy, abs=0.2)


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
