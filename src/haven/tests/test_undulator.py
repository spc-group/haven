import asyncio
import math
from io import StringIO

import pytest
from ophyd_async.testing import get_mock_put, set_mock_value
import pandas as pd

from haven.devices import PlanarUndulator
from haven.devices.undulator import BusyStatus


@pytest.fixture()
async def undulator():
    undulator = PlanarUndulator(prefix="PSS:255ID:", offset_pv="255idNP:id_offset", name="undulator")
    await undulator.connect(mock=True)
    await undulator.energy.setpoint.connect(mock=False)
    await undulator.energy.readback.connect(mock=False)
    return undulator


async def test_data_keys(undulator):
    reading = await undulator.read()
    assert set(reading.keys()) == {
        "undulator-gap",
        "undulator-gap_taper",
        "undulator-energy",
        "undulator-energy_taper",
        "undulator-energy-dial_readback",
        "undulator-total_power",
    }
    config = await undulator.read_configuration()
    assert set(config.keys()) == {
        "undulator-device",
        "undulator-device_limit",
        'undulator-energy-offset',
        'undulator-energy-precision',
        'undulator-energy-units',
        'undulator-energy_taper-precision',
        'undulator-energy_taper-units',
        'undulator-gap-precision',
        'undulator-gap-units',
        'undulator-gap_deadband',
        'undulator-gap_taper-precision',
        'undulator-gap_taper-units',
        'undulator-harmonic_value',
        'undulator-location',
        'undulator-magnet',
        'undulator-version_hpmu',
        'undulator-version_plc',
    }
    # We probably don't want hints from the undulator, just the mono
    assert undulator.hints == {}


async def test_stop_energy(undulator):
    stop_mock = get_mock_put(undulator.stop_button)
    assert not stop_mock.called
    await undulator.energy.stop()
    assert stop_mock.called


async def test_energy_unit_conversion(undulator):
    # Check setpoint
    await undulator.energy.setpoint.set(8333)
    assert await undulator.energy.dial_setpoint.get_value() == 8.333
    # Check readback
    set_mock_value(undulator.energy.dial_readback, 9.534)
    assert await undulator.energy.readback.get_value() == 9534


async def test_energy_unit_offset(undulator):
    set_mock_value(undulator.energy.offset, 10)
    await undulator.energy.setpoint.set(8333)
    assert await undulator.energy.dial_setpoint.get_value() == 8.343
    set_mock_value(undulator.energy.dial_readback, 8.583)
    assert await undulator.energy.readback.get_value() == 8573


def test_auto_offset_lookup(undulator):
    # Should fail without a lookup table
    with pytest.raises(ValueError):
        undulator.auto_offset(1500)
    # Now try again with a lookup table
    undulator._offset_table = StringIO(
        "# energy\toffset\n"
        "1000\t10\n"
        "2000\t20\n"
        "3000\t30\n"
    )
    assert undulator.auto_offset(1500) == 15
    # Out-of-bounds interpolation should fail
    with pytest.raises(ValueError):
        undulator.auto_offset(500)


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
