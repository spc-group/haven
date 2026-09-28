import pytest
import pytest_asyncio
from ophyd.utils.errors import ReadOnlyError
from ophyd_async.core import set_mock_value
from ophyd_async.testing import assert_value

from haven.devices.shutter import PssShutter, ShutterState


@pytest_asyncio.fixture()
async def shutter(sim_registry):
    """
    Example PVs:

    S25ID-PSS:SCS:OpenEPICSC
    S25ID-PSS:SCS:CloseEPICSC
    S25ID-PSS:SCS:BeamBlockingM.VAL
    """
    shutter = PssShutter(
        prefix="S255ID-PSS:SCS:",
        name="shutter",
        hutch_prefix="S255ID-PSS:StaC:",
        allow_open=True,
        allow_close=True,
    )
    await shutter.connect(mock=True)
    set_mock_value(shutter.hutch_searched, True)
    set_mock_value(shutter.user_key, True)
    set_mock_value(shutter.aps_key, True)
    return shutter


def reset_actuators(device):
    # Prepare the shutter actuator mocks as if the shutter hasn't
    # been moved
    set_mock_value(device.open, 0)
    set_mock_value(device.close, 0)


@pytest.mark.asyncio()
async def test_read_shutter(shutter):
    """The current state of the shutter should be readable.

    This makes it compatible with the ``open_shutters_wrapper``.

    """
    reading = await shutter.read()
    assert shutter.name in reading


@pytest.mark.asyncio()
async def test_shutter_setpoint(shutter):
    """When we open and close the shutter, do the right EPICS signals get
    set?

    """

    # Close the shutter
    reset_actuators(shutter)
    await shutter.set(ShutterState.CLOSED)
    await assert_value(shutter.open, False)
    await assert_value(shutter.close, True)
    # Open the shutter
    reset_actuators(shutter)
    await shutter.set(ShutterState.OPEN)
    await assert_value(shutter.open, True)
    await assert_value(shutter.close, False)


@pytest.mark.asyncio()
async def test_fail_on_hutch_unsearched(shutter):
    """When we open and close the shutter, do the right EPICS signals get
    set?

    """

    # Close the shutter
    reset_actuators(shutter)
    set_mock_value(shutter.hutch_searched, False)
    with pytest.raises(ReadOnlyError):
        await shutter.set(ShutterState.OPEN)
    await assert_value(shutter.open, False)
    await assert_value(shutter.close, False)


@pytest.mark.asyncio()
async def test_fail_on_aps_key_disabled(shutter):
    """When we open and close the shutter, do the right EPICS signals get
    set?

    """

    # Close the shutter
    reset_actuators(shutter)
    set_mock_value(shutter.aps_key, False)
    with pytest.raises(ReadOnlyError):
        await shutter.set(ShutterState.OPEN)
    await assert_value(shutter.open, False)
    await assert_value(shutter.close, False)


@pytest.mark.asyncio()
async def test_fail_on_user_key_disabled(shutter):
    """When we open and close the shutter, do the right EPICS signals get
    set?

    """

    # Close the shutter
    reset_actuators(shutter)
    set_mock_value(shutter.user_key, False)
    with pytest.raises(ReadOnlyError):
        await shutter.set(ShutterState.OPEN)
    await assert_value(shutter.open, False)
    await assert_value(shutter.close, False)


@pytest.mark.asyncio()
async def test_shutter_check_value(shutter):
    # Check for non-sense values
    with pytest.raises(ValueError):
        await shutter.set(ShutterState.FAULT)
    # Test shutter allow_close
    shutter.movable_logic.allow_close = False
    with pytest.raises(ReadOnlyError):
        await shutter.set(ShutterState.CLOSED)
    # Test shutter allow_open
    shutter.movable_logic.allow_open = False
    with pytest.raises(ReadOnlyError):
        await shutter.set(ShutterState.OPEN)


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
