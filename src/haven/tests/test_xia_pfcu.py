import time
from collections import ChainMap
from unittest import mock

import pytest
from apstools.devices.shutters import ShutterBase
from ophyd import DynamicDeviceComponent as DCpt
from ophyd.sim import make_fake_device

from haven import load_config
from haven.instrument import xia_pfcu
from haven.instrument.xia_pfcu import (
    PFCUFilter,
    PFCUFilterBank,
    PFCUShutter,
    load_xia_pfcu4s,
)


@pytest.fixture()
def shutter(xia_shutter):
    yield xia_shutter


@pytest.fixture()
def shutter_bank():
    class ShutterBank(PFCUFilterBank):
        shutters = DCpt(
            {
                "shutter_0": (
                    PFCUShutter,
                    "",
                    {"top_filter": 4, "bottom_filter": 3, "labels": {"shutters"}},
                )
            }
        )

        def __new__(cls, *args, **kwargs):
            return object.__new__(cls)

    FakeBank = make_fake_device(ShutterBank)
    bank = FakeBank(shutters=[[3, 4]])
    yield bank


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
    assert isinstance(shutter, ShutterBase)
    assert shutter.top_filter.setpoint.get() == 0
    assert shutter.bottom_filter.setpoint.get() == 0


def test_pfcu_shutter_open(shutter):
    assert shutter.state == "unknown"
    # Open the shutter, and check the
    st = shutter.set("open")
    time.sleep(0.1)
    assert shutter.top_filter.setpoint.get() == 0
    assert shutter.bottom_filter.setpoint.get() == 1


def test_pfcu_shutter_readback_signal(shutter):
    # Set the shutter position
    shutter.top_filter.readback._readback = 0
    shutter.top_filter.readback._run_subs(
        sub_type=shutter.top_filter.readback._default_sub
    )
    shutter.bottom_filter.readback._readback = 1
    shutter.bottom_filter.readback._run_subs(
        sub_type=shutter.bottom_filter.readback._default_sub
    )
    # Check that the readback signal gets updated
    assert shutter.readback.get() == "open"


def test_pfcu_shutter_bank_mask(shutter_bank):
    """A bit-mask used for determining how to set the filter bank."""
    shutter = shutter_bank.shutters.shutter_0
    assert shutter.top_mask() == 0b0001
    assert shutter.bottom_mask() == 0b0010


def test_pfcu_shutter_fast_open(shutter_bank):
    """If the PFCU filter bank is available, open both blades simultaneously."""
    shutter = shutter_bank.shutters.shutter_0
    # Set the other filters on the filter bank
    shutter_bank.readback._readback = 0b0100
    # Open the shutter, and check that the filterbank was set
    st = shutter.set("open")
    time.sleep(0.1)
    assert shutter_bank.setpoint.get() == 0b0110


def test_pfcu_shutter_close(shutter):
    assert shutter.state == "unknown"
    # Open the shutter, and check the
    shutter.set("close")
    time.sleep(0.1)
    assert shutter.top_filter.setpoint.get() == 1
    assert shutter.bottom_filter.setpoint.get() == 0


def test_pfcu_shutter_fast_close(shutter_bank):
    """If the PFCU filter bank is available, open both blades simultaneously."""
    shutter = shutter_bank.shutters.shutter_0
    # Set the other filters on the filter bank
    shutter_bank.readback._readback = 0b0100
    # Open the shutter, and check that the filterbank was set
    st = shutter.set("close")
    time.sleep(0.1)
    assert shutter_bank.setpoint.get() == 0b0101


def test_load_filters(monkeypatch):
    # Simulate the function for making the device
    # works around a bug due to the use of __new__ to make a factory
    device_maker = mock.AsyncMock()
    monkeypatch.setattr(xia_pfcu, "make_device", device_maker)
    # Call the code under test
    load_xia_pfcu4s()
    # Check that the fake ``make_device`` function was called properly
    assert device_maker.call_count == 2
    device_maker.assert_called_with(
        PFCUFilterBank,
        labels={"filter_banks"},
        name="filter_bank1",
        prefix="255idc:pfcu1:",
        shutters=[[3, 4]],
    )
    # Make a device with these arguments
    call_args = device_maker.call_args
    device = call_args.args[0](**call_args.kwargs)
    # Check that the filters have the right PVs
    filters = [device.filters.filter1, device.filters.filter2]
    assert isinstance(filters[0], PFCUFilter)
    # Check that the shutter object was created
    shutter = device.shutters.shutter_0
    assert isinstance(shutter, PFCUShutter)
    assert shutter.top_filter.material.pvname == "255idc:pfcu1:filter3_mat"
