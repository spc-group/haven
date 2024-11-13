import asyncio

import pytest
from ophyd_async.core import set_mock_value

from haven.devices.energy_positioner import EnergyPositioner


@pytest.fixture()
async def positioner():
    positioner = EnergyPositioner(
        name="energy",
        monochromator_prefix="255idMono:",
        undulator_prefix="S255ID:",
    )
    await positioner.connect(mock=True)
    await positioner.setpoint.connect(mock=False)
    await positioner.readback.connect(mock=False)
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
