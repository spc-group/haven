import asyncio
from io import StringIO

import numpy as np
import pytest
from ophyd_async.core import get_mock_put, set_mock_value
from ophyd_async.testing import assert_value
from scanspec.core import Path
from scanspec.specs import Line

from haven import exceptions
from haven.devices import PlanarUndulator
from haven.devices.undulator import UndulatorScanMode


@pytest.fixture()
async def undulator():
    undulator = PlanarUndulator(
        prefix="PSS:255ID:", offset_pv="255idNP:id_offset", name="undulator"
    )
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
        "undulator-energy-offset",
        "undulator-energy-precision",
        "undulator-energy-dial_precision",
        "undulator-energy-units",
        "undulator-energy_taper-precision",
        "undulator-energy_taper-units",
        "undulator-gap-precision",
        "undulator-gap-units",
        "undulator-gap_deadband",
        "undulator-gap_taper-precision",
        "undulator-gap_taper-units",
        "undulator-harmonic_value",
        "undulator-location",
        "undulator-magnet",
        "undulator-scan_array_length",
        "undulator-version_hpmu",
        "undulator-version_plc",
    }
    assert undulator.hints == {"fields": ["undulator-energy"]}


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
        "# energy\toffset\n" "1000\t10\n" "2000\t20\n" "3000\t30\n"
    )
    assert undulator.auto_offset(1500) == 15
    # Out-of-bounds interpolation should fail
    with pytest.raises(ValueError):
        undulator.auto_offset(500)


async def test_prepare_energy_scan(undulator, mocker):
    energies = [1000, 1100, 1200]
    spec = Line(undulator.energy, 1000, 1200, 3)
    path = Path(spec.calculate())
    set_mock_value(undulator.scan_mismatch_count, 0)
    set_mock_value(undulator.scan_gap_array_check, True)
    set_mock_value(undulator.scan_energy_array_check, True)
    set_mock_value(undulator.energy.offset, 20)
    # Simulate the gap array getting calculated
    # The EPICS array will always be 2000 values long
    array_size = 2000
    gaps = [35800, 3600, 37100]
    set_mock_value(undulator.scan_gap_array, gaps + [0] * (array_size - len(gaps)))
    # Prepare and check end point
    mocker.patch.object(undulator, "auto_offset", mocker.MagicMock(return_value=20))
    await undulator.energy.prepare(path)
    # set_mock_value(undulator.busy, 1)
    # await asyncio.sleep(0.1)
    # assert await undulator.scan_mode.get_value() == UndulatorScanMode.NORMAL
    assert await undulator.clear_scan_array.get_value() == True
    assert await undulator.scan_array_length.get_value() == 3
    np.testing.assert_equal(
        await undulator.scan_energy_array.get_value(), [1.02, 1.12, 1.22]
    )
    # # Simulate the undulator having been moved
    # set_mock_value(undulator.busy, 0)
    # await undulator.gap.readback.set(35.8)
    # await asyncio.sleep(0.1)
    # await asyncio.wait_for(status, timeout=3)
    # assert await undulator.gap.setpoint.get_value() == 35.8
    assert await undulator.scan_mode.get_value() == UndulatorScanMode.SOFTWARE_RETRIES
    # Confirm that the energy and gap iterators are set so we can move later
    np.testing.assert_equal(list(undulator._gap_iter), np.divide(gaps, 1000))
    np.testing.assert_equal(list(undulator._energy_iter), energies)


async def test_move_first_energy_scan(undulator, mocker):
    """Can we move the undulator properly to the first point a
    pre-determined energy scan?

    """
    mock_config = mocker.MagicMock()
    mock_config.feature_flag.return_value = True
    mocker.patch("haven.devices.undulator.load_config", new=mock_config)
    # Pretend we already prepared it
    undulator._energy_iter = iter([1000, 1100, 1200])
    undulator._gap_iter = iter([35.8, 36, 37.1])
    set_mock_value(undulator.scan_mode, UndulatorScanMode.SOFTWARE_RETRIES)
    undulator.energy.scan_has_moved = False
    # Now do the actual move
    set_status = undulator.energy.set(1000)
    set_mock_value(undulator.busy, 1)
    await asyncio.sleep(0.05)  # Sleep to let the move start
    assert await undulator.scan_mode.get_value() == UndulatorScanMode.NORMAL
    assert await undulator.gap.setpoint.get_value() == 35.8
    # Simulate the undulator having been moved
    set_mock_value(undulator.busy, 0)
    await undulator.gap.readback.set(35.8)
    await asyncio.wait_for(set_status, timeout=3)
    assert await undulator.scan_mode.get_value() == UndulatorScanMode.SOFTWARE_RETRIES
    # Should not update the next scan point
    assert await undulator.scan_next_point.get_value() == 0


async def test_move_next_energy_scan(undulator, mocker):
    """Can we move the undulator properly to the 2nd, 3rd, etc point as
    part of a pre-determined energy scan?

    """
    mock_config = mocker.MagicMock()
    mock_config.feature_flag.return_value = True
    mocker.patch("haven.devices.undulator.load_config", new=mock_config)
    # Pretend we already prepared it
    undulator._energy_iter = iter([1000, 1100, 1200])
    undulator._gap_iter = iter([35.8, 36, 37.1])
    set_mock_value(undulator.scan_mode, UndulatorScanMode.SOFTWARE_RETRIES)
    set_mock_value(undulator.scan_current_index, 1)
    set_mock_value(undulator.energy.velocity, 1000)  # Make timeouts reasonable
    # Now do the actual move
    set_status = undulator.energy.set(1000)
    await asyncio.sleep(0.05)
    assert await undulator.scan_next_point.get_value() == 1
    await asyncio.sleep(0.1)  # Wait for the next-point-trigger to reset
    assert await undulator.scan_next_point.get_value() == 0
    set_mock_value(undulator.energy.dial_readback, 1.0)
    await asyncio.sleep(0.1)
    await set_status


async def test_unstage(undulator):
    set_mock_value(undulator.scan_mode, UndulatorScanMode.SOFTWARE)
    await undulator.energy.unstage()
    assert await undulator.scan_mode.get_value() == UndulatorScanMode.NORMAL


@pytest.mark.parametrize("signal_name", ("energy", "gap", "energy_taper", "gap_taper"))
async def test_gap_deadband_raises(undulator, signal_name):
    set_mock_value(undulator.gap_deadband, 1)
    with pytest.raises(exceptions.InvalidUndulatorDeadband):
        await getattr(undulator, signal_name).set(0)


async def test_energy_precision(undulator):
    set_mock_value(undulator.energy.dial_precision, 4)
    await assert_value(undulator.energy.precision, 1)


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
