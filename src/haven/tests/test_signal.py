import asyncio
import math
from unittest.mock import MagicMock

import pytest
from ophyd_async.core import Device, DeviceVector
from ophyd_async.core._signal import soft_signal_rw
from ophyd_async.epics.core import epics_signal_rw, epics_signal_x
from ophyd_async.testing import get_mock_put

from haven.devices.signal import derived_signal_rw, derived_signal_x


def radius(x, y):
    return (x**2 + y**2) ** 0.5


def angle(x, y):
    return math.atan2(y, x)


# Forward transforms
async def angle_to_position(value, *, x, y):
    x_, y_ = await asyncio.gather(x.get_value(), y.get_value())
    r = radius(x_, y_)
    return {
        x: r * math.cos(value),
        y: r * math.sin(value),
    }


async def radius_to_position(r, *, x, y):
    x_, y_ = await asyncio.gather(x.get_value(), y.get_value())
    theta = angle(x_, y_)
    return {
        x: r * math.cos(theta),
        y: r * math.sin(theta),
    }


# Inverse transforms
def position_to_angle(values, *, x, y):
    return angle(values[x], values[y])


def position_to_radius(values, *, x, y):
    return radius(values[x], values[y])


class Goniometer(Device):
    def __init__(self, prefix, name=""):
        self.x = soft_signal_rw(float, initial_value=0)
        self.y = soft_signal_rw(float, initial_value=0)
        real_signals = {"x": self.x, "y": self.y}
        self.angle = derived_signal_rw(
            float,
            derived_from=real_signals,
            forward=angle_to_position,
            inverse=position_to_angle,
            initial_value=0,
        )
        self.radius = derived_signal_rw(
            float,
            derived_from=real_signals,
            forward=radius_to_position,
            inverse=position_to_radius,
            initial_value=0,
        )
        super().__init__(name=name)


@pytest.fixture()
async def device():
    dev = Goniometer("255idcVME:", name="goniometer")
    await dev.connect(mock=False)
    return dev


@pytest.mark.asyncio
async def test_derived_forward(device):
    await device.radius.set(2)
    await device.angle.set(math.pi / 4)
    assert await device.x.get_value() == pytest.approx(2 / math.sqrt(2))
    assert await device.y.get_value() == pytest.approx(2 / math.sqrt(2))


async def test_mock_subscribe():
    """This is to test the behavior of ophyd-async, not Haven."""
    base_signal = epics_signal_rw(float, "sldfkj")
    derived_signal = derived_signal_rw(float, derived_from={"base": base_signal})
    callback = MagicMock()
    await base_signal.connect(mock=True)
    await derived_signal.connect(mock=False)
    derived_signal.subscribe(callback)
    callback.reset_mock()
    assert not callback.called
    # Now change the value and check whether the mocked signal was changed
    await base_signal.set(5)
    assert callback.called


@pytest.mark.asyncio
async def test_derived_defaults(device):
    """Does the derived signal report the derived value by default."""
    # Set up a pair of signals
    real_sig0 = soft_signal_rw(float)
    real_sig1 = soft_signal_rw(float)
    derived_sig = derived_signal_rw(
        float, derived_from={"real0": real_sig0, "real1": real_sig1}
    )
    await asyncio.gather(
        real_sig0.connect(), real_sig1.connect(), derived_sig.connect()
    )
    # Check that the signals are linked going forward...
    await derived_sig.set(3.3)
    assert (await real_sig0.get_value()) == 3.3
    assert (await real_sig1.get_value()) == 3.3
    # ...and backward
    await real_sig0.set(5.1)
    await real_sig1.set(5.3)
    assert (await derived_sig.get_value()) == pytest.approx(5.2)


@pytest.mark.asyncio
async def test_derived_inverse(device):
    await device.x.set(2 / math.sqrt(2))
    await device.y.set(2 / math.sqrt(2))
    assert await device.angle.get_value() == pytest.approx(math.pi / 4)
    assert await device.radius.get_value() == pytest.approx(2)


@pytest.mark.asyncio
async def test_derived_reading(device):
    await device.x.set(2 / math.sqrt(2))
    await device.y.set(2 / math.sqrt(2))
    reading = await device.radius.read()
    assert reading[device.radius.name]["value"] == pytest.approx(2)


@pytest.mark.asyncio
async def test_derived_subscribe(device):
    last_reading = {}
    listener_is_done = asyncio.Event()

    def listener(new_reading):
        last_reading.update(new_reading)
        listener_is_done.set()

    await device.y.set(1 / math.sqrt(2))
    device.angle.subscribe(listener)
    listener_is_done = asyncio.Event()
    # Now update the device
    await device.x.set(1 / math.sqrt(2))
    await asyncio.wait_for(listener_is_done.wait(), timeout=1)
    # Check that the listener fired
    assert last_reading != {}
    assert last_reading[device.angle.name]["value"] == pytest.approx(math.pi / 4)


@pytest.mark.asyncio
async def test_derived_source(device):
    desc = await device.angle.describe()
    assert desc[device.angle.name]["source"] == "soft://goniometer-angle(x,y)"


@pytest.mark.asyncio
async def test_signal_x_trigger(device):
    signal = epics_signal_x("255idcVME:start")
    derived = derived_signal_x(derived_from={"signal": signal})
    await signal.connect(mock=True)
    await derived.connect(mock=True)
    # Now trigger the parent
    mocked_put = get_mock_put(signal)
    await derived.trigger()
    mocked_put.assert_called_once_with(None, wait=True)


async def test_device_vector_parent():
    class MyDevice(Device):
        def __init__(self, name):
            self.my_signal = soft_signal_rw(float)
            self.channels = DeviceVector({0: soft_signal_rw(float)})
            super().__init__(name=name)

    my_device = MyDevice(name="my_device")
    await my_device.connect(mock=True)
    # Good tests
    assert my_device.my_signal.name == "my_device-my_signal"
    assert my_device.my_signal.parent is my_device
    assert my_device.channels.name == "my_device-channels"
    assert my_device.channels.parent is my_device
    assert my_device.channels[0].name == "my_device-channels-0"
    # Bad tests
    assert my_device.channels[0].parent is my_device.channels
