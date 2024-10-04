import pytest

from haven.devices.xia_pfcu import PFCUFilter, PFCUFilterBank, PFCUShutter, ShutterState


@pytest.fixture()
def shutter(xia_shutter):
    yield xia_shutter


@pytest.fixture()
def shutter_bank(xia_shutter_bank):
    yield xia_shutter_bank


def test_shutter_factory():
    """Check that a shutter device is created if requested."""
    filterbank = PFCUFilterBank(
        prefix="255id:pfcu0:", name="filter_bank_0", shutters=[(2, 3)]
    )  #
    assert filterbank.prefix == "255id:pfcu0:"
    assert filterbank.name == "filter_bank_0"
    assert hasattr(filterbank, "shutters")
    assert isinstance(filterbank.shutters.shutter_0, PFCUShutter)
    assert hasattr(filterbank, "shutters")
    assert isinstance(filterbank.filters.filter1, PFCUFilter)
    assert filterbank.filters.filter1.prefix == "255id:pfcu0:filter1"
    assert isinstance(filterbank.filters.filter4, PFCUFilter)
    assert not hasattr(filterbank.filters, "filter2")
    assert not hasattr(filterbank.filters, "filter3")


def test_pfcu_shutter_signals(shutter):
    # Check initial state
    assert shutter.top_filter.setpoint.get() == 0
    assert shutter.bottom_filter.setpoint.get() == 0


def test_pfcu_shutter_readback(shutter):
    # Set the shutter position
    readback = shutter.parent.parent.readback
    readback._readback = 0b0010
    readback._run_subs(sub_type=readback._default_sub)
    # Check that the readback signal gets updated
    assert shutter.readback.get() == ShutterState.OPEN


def test_pfcu_shutter_bank_mask(shutter_bank):
    """A bit-mask used for determining how to set the filter bank."""
    shutter = shutter_bank.shutters.shutter_0
    assert shutter.setpoint.top_mask() == 0b0001
    assert shutter.setpoint.bottom_mask() == 0b0010


def test_pfcu_shutter_open(shutter_bank):
    """If the PFCU filter bank is available, open both blades simultaneously."""
    shutter = shutter_bank.shutters.shutter_0
    # Set the other filters on the filter bank
    shutter_bank.readback._readback = 0b0100
    # Open the shutter, and check that the filterbank was set
    shutter.setpoint.set(ShutterState.OPEN).wait(timeout=1)
    assert shutter_bank.setpoint.get() == 0b0110


def test_pfcu_shutter_close(shutter_bank):
    """If the PFCU filter bank is available, open both blades simultaneously."""
    shutter = shutter_bank.shutters.shutter_0
    # Set the other filters on the filter bank
    shutter_bank.readback._readback = 0b0100
    # Open the shutter, and check that the filterbank was set
    shutter.setpoint.set(ShutterState.CLOSED).wait(timeout=1)
    assert shutter_bank.setpoint.get() == 0b0101


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
