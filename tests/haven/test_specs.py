import logging

import numpy as np
import pytest

from haven import (
    energy_to_wavenumber,
)
from haven.specs import EnergyRegion, KWeighted, WavenumberRegion

logging.basicConfig(level=logging.INFO)

energy_range_parameters = [
    # (start, end, num, E0, expected_energies)
    (8300, 8400, 201, np.linspace(8300, 8400, num=201)),  # Example values
    (1, 1.3, 4, [1, 1.1, 1.2, 1.3]),  # Known float rounding error
    (1.3, 1.0, 4, [1.3, 1.2, 1.1, 1.0]),  # Reverse direction
]


@pytest.mark.parametrize("start,stop,num,expected_energies", energy_range_parameters)
def test_energy_spec(start, stop, num, expected_energies):
    """Test the ERange class for calculating energy points."""
    e_region = EnergyRegion("x", start, stop, num)
    (frame,) = e_region.calculate()
    np.testing.assert_almost_equal(frame.midpoints["x"], np.asarray(expected_energies))


def test_energy_spec_with_E0():
    E0 = 8730
    e_region = EnergyRegion("x", -20, 50, 31, E0=E0)
    (frame,) = e_region.calculate()
    np.testing.assert_almost_equal(
        frame.midpoints["x"], np.linspace(8710, 8780, num=31)
    )


def test_wavenumber_spec():
    E0 = 17038
    region = WavenumberRegion("x", 2.8, 14, 21, E0=E0)
    (frame,) = region.calculate()
    energies = frame.midpoints["x"]
    wavenumbers = energy_to_wavenumber(energies - E0)
    np.testing.assert_almost_equal(wavenumbers[0], 2.8)
    np.testing.assert_almost_equal(wavenumbers[-1], 14)
    # Verify the results compared to Shelly's spreadsheet
    E_min = np.min(energies)
    np.testing.assert_equal(energies[0], E_min)
    np.testing.assert_almost_equal(
        energies[-1], 746.7568692 + 17038, decimal=3
    )  # Athena value


def test_constant_duration():
    region = KWeighted(
        spec=EnergyRegion("x", -10, 10, num=4, E0=8730), base_duration=0.1
    )
    (frame,) = region.calculate()
    np.testing.assert_equal(frame.duration, [0.1, 0.1, 0.1, 0.1])


def test_weighted_duration():
    region = KWeighted(
        spec=WavenumberRegion("x", 2, 4, num=5, E0=8730),
        base_duration=1,
        k_weight=1,
        E0=8730,
    )
    (frame,) = region.calculate()
    np.testing.assert_almost_equal(frame.duration, [2, 2.5, 3, 3.5, 4])


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
