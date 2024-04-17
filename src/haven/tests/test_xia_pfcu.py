import pytest

from apstools.devices.shutters import ShutterBase
from ophyd.sim import make_fake_device

from haven.instrument.xia_pfcu import PFCUFilter, PFCUFilterBank, PFCUShutter


@pytest.fixture()
def shutter():
    FakeShutter = make_fake_device(PFCUShutter)
    shtr = FakeShutter(
        top_filter="255idc:pfcu0:", bottom_filter="255idc:pfcu1:", name="shutter"
    )
    return shtr


def test_shutter_factory():
    """Check that a shutter device is created if requested."""
    filterbank = PFCUFilterBank(shutters=[(2, 3)])  #
    assert hasattr(filterbank, "shutters")
    assert isinstance(filterbank.shutters.shutter0, PFCUShutter)
    assert hasattr(filterbank, "shutters")
    assert isinstance(filterbank.filters.filter1, PFCUFilter)
    assert isinstance(filterbank.filters.filter4, PFCUFilter)
    assert not hasattr(filterbank.filters, "filter2")
    assert not hasattr(filterbank.filters, "filter3")


def test_pfcu_shutter_signals(shutter):
    # Check initial state
    assert isinstance(shutter, ShutterBase)
    assert shutter.top_filter.setpoint.get() == 0
    assert shutter.bottom_filter.setpoint.get() == 0


def test_pfcu_shutter_open(shutter):
    assert shutter.state == "unknown"
    # Open the shutter, and check the 
    shutter.set("open").wait(timeout=3)
    assert shutter.top_filter.setpoint.get() == 0
    assert shutter.bottom_filter.setpoint.get() == 1


def test_pfcu_shutter_close(shutter):
    assert shutter.state == "unknown"
    # Open the shutter, and check the 
    shutter.set("close").wait(timeout=3)
    assert shutter.top_filter.setpoint.get() == 1
    assert shutter.bottom_filter.setpoint.get() == 0
