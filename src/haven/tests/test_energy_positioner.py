import asyncio

import pytest
from ophyd_async.testing import get_mock_put, set_mock_value

from haven.devices.energy_positioner import EnergyPositioner
from haven.devices.xray_source import BusyStatus


@pytest.fixture()
async def positioner():
    positioner = EnergyPositioner(
        name="energy",
        monochromator_prefix="255idMono:",
        undulator_prefix="S255ID:",
    )
    await positioner.connect(mock=True)
    set_mock_value(positioner.monochromator.energy.velocity, 5000)
    return positioner


async def test_set_energy(positioner):
    # Set up dependent values
    set_mock_value(positioner.monochromator.id_offset, 150)
    # Change the energy
    await positioner.set(10000, timeout=3, wait=False)
    # Trick the Undulator into being done
    await asyncio.sleep(0.05)  # Let the event loop run
    # Check that all the sub-components were set properly
    assert await positioner.monochromator.energy.user_setpoint.get_value() == 10000
    assert await positioner.undulator.energy.setpoint.get_value() == 10.150


async def test_real_to_pseudo_positioner(positioner):
    set_mock_value(positioner.monochromator.energy.user_readback, 5000.0)
    # Check that the pseudo single is updated
    reading = await positioner.read()
    assert reading["energy"]["value"] == 5000.0


async def test_disable_id_tracking(positioner):
    energy = positioner
    # Turn on tracking to start with
    set_mock_value(energy.monochromator.id_tracking, 1)
    set_mock_value(energy.velocity, 100)
    # Set the energy
    status = energy.set(5000, wait=False)
    # Trick the Undulator into being done
    set_mock_value(positioner.undulator.energy.done, BusyStatus.BUSY)
    await asyncio.sleep(0.05)  # Let the event loop run
    set_mock_value(positioner.undulator.energy.done, BusyStatus.DONE)
    await status
    # Check that ID tracking was disabled
    tracking_mock = get_mock_put(positioner.monochromator.id_tracking)
    assert tracking_mock.call_count == 2
    assert tracking_mock.call_args_list[0].args[0] == 0
    assert tracking_mock.call_args_list[1].args[0] == 1


async def test_reading(positioner):
    assert positioner.hints["fields"] == ["energy"]
    reading = await positioner.read()
    expected_signals = [
        "energy-undulator-energy",
        "energy-undulator-energy-setpoint",
        "energy-undulator-gap",
        "energy-undulator-gap-setpoint",
        "energy-undulator-gap_taper",
        "energy-undulator-gap_taper-setpoint",
        "energy-undulator-energy_taper",
        "energy-undulator-energy_taper-setpoint",
        "energy-setpoint",
        "energy-monochromator-roll2",
        "energy-monochromator-pitch2",
        "energy-monochromator-energy",
        "energy-monochromator-vert",
        "energy-monochromator-horiz",
        "energy-monochromator-bragg",
        "energy-monochromator-offset",
        "energy-monochromator-gap",
        "energy",
    ]
    assert sorted(list(reading.keys())) == sorted(expected_signals)


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
