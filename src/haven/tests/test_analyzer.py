import time

import numpy as np
import pytest
from ophyd.sim import make_fake_device

from haven.instrument import analyzer

um_per_mm = 1000


energy_to_wavelength_values = [
    # (eV,      meters)
    (61992.35 , 0.2e-10),
    (24796.94 , 0.5e-10),
    (12398.47 , 1.0e-10),
    ( 8041.555, 1.5418e-10),
    ( 6199.235, 2.00e-10),
    ( 2000.,    6.19924e-10),
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
    assert pytest.approx(analyzer.wavelength_to_bragg(wavelength, d=d_spacing), rel=0.001) == theta


analyzer_values = [
    # (bragg, alpha, beta, x,      z)
    (70,      15,    25,   47.79,  47.60),
    (80,      7,     87,   2.65,   49.40),
    (60,      20,    80,   9.87,   43.56),
    (65,      0,     65,   19.15,  41.07),
    (80,      30,    110,  -16.32, 46.98),
]


@pytest.fixture()
def xtal(sim_registry):
    FakeAnalyzer = make_fake_device(analyzer.Analyzer)
    xtal = FakeAnalyzer(name="analyzer", x_motor_pv="", z_motor_pv="")
    # Set default values for xtal parameters
    d = 1.637 * 1e-10  # Si 311 converted to meters
    xtal.d_spacing.set(d).wait()
    xtal.rowland_diameter.set(0.500).wait()
    return xtal


@pytest.mark.parametrize("bragg,alpha,beta,x,z", analyzer_values)
def test_rowland_circle_forward(xtal, bragg, alpha, beta, x, z):
    xtal.wedge_angle.set(np.radians(beta)).wait()
    d = xtal.d_spacing.get()
    bragg = np.radians(bragg)
    energy = analyzer.bragg_to_energy(bragg, d=d)
    wavelength = analyzer.bragg_to_wavelength(bragg, d=d)
    # Check the result is correct (convert cm -> m)
    assert xtal.forward(energy, np.radians(alpha)) == (x / 100, z / 100)

# @pytest.mark.xfail
# def test_rowland_circle_inverse():
#     rowland = instantiate_fake_device(
#         lerix.RowlandPositioner,
#         name="rowland",
#         x_motor_pv="",
#         y_motor_pv="",
#         z_motor_pv="",
#         z1_motor_pv="",
#     )
#     # Check one set of values
#     result = rowland.inverse(
#         x=500.0,  # x
#         y=375.0,  # y
#         z=216.50635094610968,  # z
#         z1=1.5308084989341912e-14,  # z1
#     )
#     assert result == pytest.approx((500, 60, 30))
#     # # Check one set of values
#     # result = rowland.forward(500, 80.0, 0.0)
#     # assert result == pytest.approx((
#     #     484.92315519647707 * um_per_mm,  # x
#     #     0.0 * um_per_mm,  # y
#     #     171.0100716628344 * um_per_mm,  # z
#     #     85.5050358314172 * um_per_mm,  # z1
#     # ))
#     # # Check one set of values
#     # result = rowland.forward(500, 70.0, 10.0)
#     # assert result == pytest.approx((
#     #     484.92315519647707 * um_per_mm,  # x
#     #     109.92315519647711 * um_per_mm,  # y
#     #     291.6982175363274 * um_per_mm,  # z
#     #     75.19186659021767 * um_per_mm,  # z1
#     # ))
#     # # Check one set of values
#     # result = rowland.forward(500, 75.0, 15.0)
#     # assert result == pytest.approx((
#     #     500.0 * um_per_mm,  # x
#     #     124.99999999999994 * um_per_mm,  # y
#     #     216.50635094610965 * um_per_mm,  # z
#     #     2.6514380968122676e-14 * um_per_mm,  # z1
#     # ))
#     # # Check one set of values
#     # result = rowland.forward(500, 71.0, 10.0)
#     # assert result == pytest.approx((
#     #     487.7641290737884 * um_per_mm,  # x
#     #     105.28431301548724 * um_per_mm,  # y
#     #     280.42235703910393 * um_per_mm,  # z
#     #     68.41033299999741 * um_per_mm,  # z1
#     # ))


# def test_rowland_circle_component():
#     device = instantiate_fake_device(
#         lerix.LERIXSpectrometer, prefix="255idVME", name="lerix"
#     )
#     device.rowland.x.user_setpoint._use_limits = False
#     device.rowland.y.user_setpoint._use_limits = False
#     device.rowland.z.user_setpoint._use_limits = False
#     device.rowland.z1.user_setpoint._use_limits = False
#     # Set pseudo axes
#     statuses = [
#         device.rowland.D.set(500.0),
#         device.rowland.theta.set(60.0),
#         device.rowland.alpha.set(30.0),
#     ]
#     # [s.wait() for s in statuses]  # <- this should work, need to come back to it
#     time.sleep(0.1)
#     # Check that the virtual axes were set
#     result = device.rowland.get(use_monitor=False)
#     assert result.x.user_setpoint == pytest.approx(500.0 * um_per_mm)
#     assert result.y.user_setpoint == pytest.approx(375.0 * um_per_mm)
#     assert result.z.user_setpoint == pytest.approx(216.50635094610968 * um_per_mm)
#     assert result.z1.user_setpoint == pytest.approx(1.5308084989341912e-14 * um_per_mm)


# def test_load_lerix_spectrometers(sim_registry):
#     lerix.load_lerix_spectrometers()
#     device = sim_registry.find(name="lerix")
#     assert device.name == "lerix"
#     assert device.x.prefix == "255idVME:m1"
#     assert device.y.prefix == "255idVME:m2"
#     assert device.z.prefix == "255idVME:m3"
#     assert device.z1.prefix == "255idVME:m4"


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
