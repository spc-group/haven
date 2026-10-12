import asyncio

import pytest
import pytest_asyncio
from bluesky import RunEngine
from bluesky import plan_stubs as bps
from bluesky.utils import ProgressBarManager
from ophyd_async.core import set_mock_value
from ophyd_async.testing import assert_value

from haven.devices.xia_pfcu import (
    FilterState,
    PFCUFilter,
    PFCUFilterBank,
    PFCUShutter,
    ShutterState,
    update_filter_state,
)


@pytest_asyncio.fixture()
async def filter_bank(sim_registry):
    bank = PFCUFilterBank(
        prefix="255id:pfcu4:", name="xia_filter_bank", shutters=[(1, 2)]
    )
    await bank.connect(mock=True)
    sim_registry.register(bank)
    yield bank


@pytest_asyncio.fixture()
async def shutter(filter_bank):
    shutter = filter_bank.shutters[0]
    await asyncio.gather(
        # shutter.setpoint.connect(mock=False),
        # shutter.readback.connect(mock=False),
        shutter.top_filter.readback.connect(mock=False),
        shutter.bottom_filter.readback.connect(mock=False),
    )
    yield shutter


@pytest_asyncio.fixture()
async def filter(filter_bank):
    filter = filter_bank.filters[0]
    await filter.readback.connect(mock=False)
    yield filter


@pytest.mark.asyncio()
async def test_filter_bank_location(filter_bank):
    await filter_bank.set(0b0101)
    # String representation is LSB first so reverse the order
    await assert_value(filter_bank.raw_setpoint, "1010")
    await assert_value(filter_bank.raw_readback, "1010")
    assert await filter_bank.locate() == {"readback": 0b0101, "setpoint": 0b0101}


@pytest.mark.asyncio()
async def test_filter_location(filter_bank):
    """Check that a filter can be located."""
    filter = filter_bank.filters[0]
    assert filter._position == 0
    await filter_bank.setpoint.set(0b0001)
    location = await filter.locate()
    assert location == {"setpoint": FilterState.IN, "readback": FilterState.IN}


@pytest.mark.asyncio()
async def test_shutter_location(filter_bank):
    """Check that a shutter can be located."""
    shutter = filter_bank.shutters[0]
    print(shutter._top_filter_idx, shutter._bottom_filter_idx)
    assert shutter._top_filter_idx == 1
    assert shutter._bottom_filter_idx == 2
    await filter_bank.setpoint.set(0b0101)
    location = await shutter.locate()
    assert location == {"setpoint": ShutterState.OPEN, "readback": ShutterState.OPEN}


def test_shutter_devices(filter_bank):
    """Check that a shutter device is created if
    requested."""
    assert hasattr(filter_bank, "shutters")
    assert isinstance(filter_bank.shutters[0], PFCUShutter)
    assert "fast_shutters" in filter_bank.shutters[0]._ophyd_labels_
    assert (
        filter_bank.shutters[0].top_filter.material.source
        == "mock+ca://255id:pfcu4:filter2_mat"
    )
    assert hasattr(filter_bank, "filters")
    assert isinstance(filter_bank.filters[0], PFCUFilter)
    assert filter_bank.filters[0].material.source == "mock+ca://255id:pfcu4:filter1_mat"
    assert isinstance(filter_bank.filters[3], PFCUFilter)
    # Make sure the shutter blades are not listed as filters
    assert 1 not in filter_bank.filters.keys()
    assert 2 not in filter_bank.filters.keys()


@pytest.mark.asyncio()
async def test_shutter_reading(shutter):
    """Ensure the shutter can be read.

    Needed for compatibility with the ``open_shutters_wrapper``.

    """
    assert shutter.readback.name == shutter.name
    reading = await shutter.read()
    assert shutter.name in reading


@pytest.mark.parametrize(
    "original, position, state, expected",
    [
        (0b0000, 0, 1, 0b0001),
        (0b0000, 1, 1, 0b0010),
        (0b0100, 2, 0, 0b0000),
        (0b1111, 1, 0, 0b1101),
    ],
)
def test_update_filter_state(original, position, state, expected):
    assert update_filter_state(original, position, state) == expected


@pytest.mark.asyncio()
async def test_move_filter(filter_bank):
    """If the PFCU filter bank is available, open both blades simultaneously."""
    filter = filter_bank.filters[0]
    # Set the other filters on the filter bank
    set_mock_value(filter_bank.raw_readback, "1001")
    # Open the shutter, and check that the filterbank was set
    await filter.set(FilterState.OUT.value)
    # (LSB first)
    assert await filter_bank.raw_setpoint.get_value() == "0001"


@pytest.mark.asyncio()
async def test_shutter_open(filter_bank):
    """If the PFCU filter bank is available, open both blades simultaneously."""
    shutter = filter_bank.shutters[0]
    # Set the other filters on the filter bank
    set_mock_value(filter_bank.raw_readback, "1001")
    # Open the shutter, and check that the filterbank was set
    await shutter.set(ShutterState.OPEN.value)
    # (LSB first)
    assert await filter_bank.raw_setpoint.get_value() == "1011"


@pytest.mark.asyncio()
async def test_shutter_close(filter_bank, shutter):
    """If the PFCU filter bank is available, open both blades simultaneously."""
    # Set the other filters on the filter bank
    set_mock_value(filter_bank.raw_readback, "1001")
    # Open the shutter, and check that the filterbank was set
    await shutter.set(ShutterState.CLOSED)
    # (LSB first)
    assert await filter_bank.raw_setpoint.get_value() == "1101"


@pytest.mark.asyncio()
async def test_filter_readback(filter_bank):
    filter = filter_bank.filters[0]
    set_mock_value(filter_bank.raw_readback, "1000")  # LSB first
    assert await filter.readback.get_value() == FilterState.IN


@pytest.mark.asyncio()
async def test_filter_bank_progress_bar_compatibility(filter_bank, mocker):
    """The progress reported by set() must survive bluesky's progress bar."""
    RE = RunEngine({})
    update_mock = mocker.patch("bluesky.utils.TerminalProgressBar.update")
    pbar_manager = ProgressBarManager()
    RE.waiting_hook = pbar_manager
    updates = []
    RE(bps.mv(filter_bank, 0b0001))
    assert update_mock.call_count == 0


@pytest.mark.asyncio()
async def test_shutter_progress_bar_compatibility(shutter, mocker):
    """The progress reported by set() must survive bluesky's progress bar."""
    RE = RunEngine({})
    update_mock = mocker.patch("bluesky.utils.TerminalProgressBar.update")
    pbar_manager = ProgressBarManager()
    RE.waiting_hook = pbar_manager
    updates = []
    RE(bps.mv(shutter, ShutterState.CLOSED))
    assert update_mock.call_count == 0


@pytest.mark.asyncio()
async def test_filter_progress_bar_compatibility(filter_bank, mocker):
    """The progress reported by set() must survive bluesky's progress bar."""
    RE = RunEngine({})
    update_mock = mocker.patch("bluesky.utils.TerminalProgressBar.update")
    pbar_manager = ProgressBarManager()
    RE.waiting_hook = pbar_manager
    updates = []
    RE(bps.mv(filter_bank.filters[0], FilterState.IN))
    assert update_mock.call_count == 0


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
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
