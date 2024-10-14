import asyncio

import pytest
from ophyd.sim import instantiate_fake_device
from ophyd_async.core import get_mock_put, set_mock_value

from haven.devices.xray_source import PlanarUndulator


@pytest.fixture()
async def undulator():
    undulator = instantiate_fake_device(
        PlanarUndulator, prefix="PSS:255ID:", name="undulator"
    )
    await undulator.connect(mock=True)
    return undulator


async def test_set_energy(undulator):
    start_mock = get_mock_put(undulator.start_button)
    setpoint_mock = get_mock_put(undulator.energy.setpoint)
    # Set the energy
    status = undulator.energy.set(5)
    # Give the set coro time to setup up subscriptions
    await asyncio.sleep(0.05)  
    # Fake the done PV getting updated
    set_mock_value(undulator.done, 1)
    # Check that the signals got set properly
    await status
    assert undulator.energy.setpoint.get() == 5
    assert undulator.start_button.get() == 1


async def test_stop_energy(undulator):
    stop_mock = get_mock_put(undulator.stop_button)
    assert not stop_mock.called
    await undulator.energy.stop()
    assert stop_mock.called

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
