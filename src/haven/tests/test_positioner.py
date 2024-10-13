import asyncio
import pytest

from ophyd_async.core import set_mock_value
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw, epics_signal_x

from haven.positioner import Positioner


class TestPositioner(Positioner):
    done_value = 1
    
    def __init__(self, name: str = ""):
        self.setpoint = epics_signal_rw(float, ".VAL")
        self.readback = epics_signal_r(float, ".RBV")
        self.actuate = epics_signal_x("StartC.VAL")
        self.done = epics_signal_r(int, "BusyDeviceM.VAL")
        self.stop_signal = epics_signal_rw(int, "StopC.VAL")
        self.precision = epics_signal_rw(int, ".PREC")
        self.velocity = epics_signal_rw(float, ".VELO")
        self.units = epics_signal_rw(str, ".EGU")
        super().__init__(name=name)


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
    await asyncio.sleep(0.05)  # Let the subscription get set up
    set_mock_value(positioner.done, 1)
    await status
