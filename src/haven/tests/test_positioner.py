import asyncio

import pytest
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_x
from ophyd_async.testing import get_mock_put, set_mock_value

from haven.positioner import Positioner


class TestPositioner(Positioner):
    done_value = 1

    def __init__(self, name: str = "", put_complete=False):
        self.setpoint = epics_signal_rw(float, ".VAL")
        self.readback = epics_signal_r(float, ".RBV")
        self.actuate = epics_signal_x("StartC.VAL")
        self.done = epics_signal_r(int, "BusyDeviceM.VAL")
        self.stop_signal = epics_signal_rw(int, "StopC.VAL")
        self.precision = epics_signal_rw(int, ".PREC")
        self.velocity = epics_signal_rw(float, ".VELO")
        self.units = epics_signal_rw(str, ".EGU")
        super().__init__(name=name, put_complete=put_complete)


@pytest.fixture()
async def positioner():
    positioner = TestPositioner()
    await positioner.connect(mock=True)
    await positioner.velocity.set(5)
    return positioner


def test_has_signals(positioner):
    assert hasattr(positioner, "setpoint")
    assert hasattr(positioner, "readback")


async def test_set_with_done_actuate(positioner):
    status = positioner.set(5.3)
    set_mock_value(positioner.done, 0)
    await asyncio.sleep(0.01)  # Let event loop run
    set_mock_value(positioner.done, 1)
    await status


async def test_set_with_readback(positioner):
    """Use the readback value to determine when the move is complete."""
    # Remove the done signal to force monitoring readback
    del positioner.done
    # Do the move
    status = positioner.set(5.3)
    set_mock_value(positioner.readback, 5.3)
    await status


async def test_set_with_put_complete():
    positioner = TestPositioner(put_complete=True)
    await positioner.connect(mock=True)
    await positioner.velocity.set(5)
    # Just make sure it doesn't time-out
    await positioner.set(13)


async def test_min_move(positioner):
    """Check that we can specify how small of a move should be ignored."""
    positioner.put_complete = True
    positioner.min_move = 5
    set_mock_value(positioner.readback, 10)
    # Move the positioner
    await positioner.set(12)
    # Check that it didn't actually move anything
    assert not get_mock_put(positioner.setpoint).called
