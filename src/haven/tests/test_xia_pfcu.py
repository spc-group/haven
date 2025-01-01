import pytest
from ophyd_async.testing import set_mock_value

from haven.devices.xia_pfcu import PFCUFilter, PFCUFilterBank, PFCUShutter, ShutterState, FilterPosition


@pytest.fixture()
async def filter_bank(sim_registry):
    bank = PFCUFilterBank(prefix="255id:pfcu4:", name="xia_filter_bank", shutters=[(1, 2)])
    await bank.connect(mock=True)
    await bank.shutters[0].setpoint.connect(mock=False)
    await bank.shutters[0].readback.connect(mock=False)
    sim_registry.register(bank)
    yield bank


@pytest.fixture()
def shutter(filter_bank):
    yield filter_bank.shutters[0]


def test_shutter_devices(filter_bank):
    """Check that a shutter device is created if
    requested."""
    assert hasattr(filter_bank, "shutters")
    assert isinstance(filter_bank.shutters[0], PFCUShutter)
    assert "fast_shutters" in filter_bank.shutters[0]._ophyd_labels_
    assert filter_bank.shutters[0].top_filter.material.source == "mock+ca://255id:pfcu4:filter2_mat"
    assert hasattr(filter_bank, "filters")
    assert isinstance(filter_bank.filters[0], PFCUFilter)
    assert filter_bank.filters[0].material.source == "mock+ca://255id:pfcu4:filter1_mat"
    assert isinstance(filter_bank.filters[3], PFCUFilter)
    # Make sure the shutter blades are not listed as filters
    assert 1 not in filter_bank.filters.keys()
    assert 2 not in filter_bank.filters.keys()


async def test_pfcu_shutter_signals(shutter):
    # Check initial state
    assert await shutter.top_filter.setpoint.get_value() == FilterPosition.OUT
    assert await shutter.bottom_filter.setpoint.get_value() == FilterPosition.OUT


async def test_pfcu_shutter_readback(filter_bank, shutter):
    # Set the shutter position
    set_mock_value(filter_bank.readback, 0b0010)
    # Check that the readback signal gets updated
    assert await shutter.readback.get_value() == ShutterState.OPEN
    # Set the shutter position
    set_mock_value(filter_bank.readback, 0b0100)
    # Check that the readback signal gets updated
    assert await shutter.readback.get_value() == ShutterState.CLOSED


async def test_pfcu_shutter_reading(shutter):
    """Ensure the shutter can be read.

    Needed for compatibility with the ``open_shutters_wrapper``.

    """
    # Set the shutter position
    reading = await shutter.read()
    assert shutter.name in reading


def test_pfcu_shutter_mask(shutter):
    """A bit-mask used for determining how to set the filter bank."""
    assert shutter.top_mask() == 0b0100
    assert shutter.bottom_mask() == 0b0010


async def test_pfcu_shutter_open(filter_bank, shutter):
    """If the PFCU filter bank is available, open both blades simultaneously."""
    # Set the other filters on the filter bank
    set_mock_value(filter_bank.readback, 0b1001)
    # Open the shutter, and check that the filterbank was set
    await shutter.setpoint.set(ShutterState.OPEN)
    assert await filter_bank.setpoint.get_value() == 0b1011


async def test_pfcu_shutter_close(filter_bank, shutter):
    """If the PFCU filter bank is available, open both blades simultaneously."""
    # Set the other filters on the filter bank
    set_mock_value(filter_bank.readback, 0b1001)
    # Open the shutter, and check that the filterbank was set
    await shutter.setpoint.set(ShutterState.CLOSED)
    assert await filter_bank.setpoint.get_value() == 0b1101


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
