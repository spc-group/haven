import asyncio
from unittest import mock

import pytest
from ophyd_async.testing import get_mock_put

from haven.devices.srs570 import GainSignal, SRS570PreAmplifier


@pytest.fixture()
async def preamp():
    preamp = SRS570PreAmplifier("255idcVEM:SR02:", name="")
    # Derived signals should not be mocked
    await preamp.connect(mock=True)
    await asyncio.gather(
        preamp.gain_level.connect(mock=False),
        preamp.gain.connect(mock=False),
        preamp.gain_db.connect(mock=False),
    )
    return preamp


# Known settling times measured from the I0 SR-570 at 25-ID-C
settling_times = {
    # (sensitivity_value, sensitivity_unit, gain_mode): settle_time
    # pA/V
    ("1", "pA/V", "HIGH BW"): 2.5,  # 1 pA/V
    ("2", "pA/V", "HIGH BW"): 2.0,
    ("5", "pA/V", "HIGH BW"): 2.0,
    ("10", "pA/V", "HIGH BW"): 0.5,
    ("20", "pA/V", "HIGH BW"): 0.5,
    ("50", "pA/V", "HIGH BW"): 0.5,  # 50 pA/V
    ("100", "pA/V", "HIGH BW"): 0.5,
    ("200", "pA/V", "HIGH BW"): 0.5,
    ("500", "pA/V", "HIGH BW"): 0.5,
    # nA/V
    ("1", "nA/V", "HIGH BW"): 0.5,
    ("2", "nA/V", "HIGH BW"): 0.5,  # 2 nA/V
    ("5", "nA/V", "HIGH BW"): 0.5,
    ("10", "nA/V", "HIGH BW"): 0.5,
    ("20", "nA/V", "HIGH BW"): 0.5,
    ("50", "nA/V", "HIGH BW"): 0.5,
    ("100", "nA/V", "HIGH BW"): 0.5,  # 100 nA/V
    ("200", "nA/V", "HIGH BW"): 0.5,
    ("500", "nA/V", "HIGH BW"): 0.5,
    # μA/V
    ("1", "uA/V", "HIGH BW"): 0.5,
    ("2", "uA/V", "HIGH BW"): 0.5,
    ("5", "uA/V", "HIGH BW"): 0.5,  # 5 μA/V
    ("10", "uA/V", "HIGH BW"): 0.5,
    ("20", "uA/V", "HIGH BW"): 0.5,
    ("50", "uA/V", "HIGH BW"): 0.5,
    ("100", "uA/V", "HIGH BW"): 0.5,
    ("200", "uA/V", "HIGH BW"): 0.5,  # 200 μA/V
    ("500", "uA/V", "HIGH BW"): 0.5,
    # mA/V
    ("1", "mA/V", "HIGH BW"): 0.5,
    ("2", "mA/V", "HIGH BW"): None,
    ("5", "mA/V", "HIGH BW"): None,
    ("10", "mA/V", "HIGH BW"): None,
    ("20", "mA/V", "HIGH BW"): None,
    ("50", "mA/V", "HIGH BW"): None,
    ("100", "mA/V", "HIGH BW"): None,
    ("200", "mA/V", "HIGH BW"): None,
    ("500", "mA/V", "HIGH BW"): None,
    # pA/V
    ("1", "pA/V", "LOW NOISE"): 3.0,
    ("2", "pA/V", "LOW NOISE"): 2.5,
    ("5", "pA/V", "LOW NOISE"): 2.0,
    ("10", "pA/V", "LOW NOISE"): 2.0,
    ("20", "pA/V", "LOW NOISE"): 1.75,
    ("50", "pA/V", "LOW NOISE"): 1.5,
    ("100", "pA/V", "LOW NOISE"): 1.25,
    ("200", "pA/V", "LOW NOISE"): 0.5,
    ("500", "pA/V", "LOW NOISE"): 0.5,
    # nA/V
    ("1", "nA/V", "LOW NOISE"): 0.5,
    ("2", "nA/V", "LOW NOISE"): 0.5,
    ("5", "nA/V", "LOW NOISE"): 0.5,
    ("10", "nA/V", "LOW NOISE"): 0.5,
    ("20", "nA/V", "LOW NOISE"): 0.5,
    ("50", "nA/V", "LOW NOISE"): 0.5,
    ("100", "nA/V", "LOW NOISE"): 0.5,
    ("200", "nA/V", "LOW NOISE"): 0.5,
    ("500", "nA/V", "LOW NOISE"): 0.5,
    # μA/V
    ("1", "uA/V", "LOW NOISE"): 0.5,
    ("2", "uA/V", "LOW NOISE"): 0.5,
    ("5", "uA/V", "LOW NOISE"): 0.5,
    ("10", "uA/V", "LOW NOISE"): 0.5,
    ("20", "uA/V", "LOW NOISE"): 0.5,
    ("50", "uA/V", "LOW NOISE"): 0.5,
    ("100", "uA/V", "LOW NOISE"): 0.5,
    ("200", "uA/V", "LOW NOISE"): 0.5,
    ("500", "uA/V", "LOW NOISE"): 0.5,
    # mA/V
    ("1", "mA/V", "LOW NOISE"): 0.5,
    ("2", "mA/V", "LOW NOISE"): None,
    ("5", "mA/V", "LOW NOISE"): None,
    ("10", "mA/V", "LOW NOISE"): None,
    ("20", "mA/V", "LOW NOISE"): None,
    ("50", "mA/V", "LOW NOISE"): None,
    ("100", "mA/V", "LOW NOISE"): None,
    ("200", "mA/V", "LOW NOISE"): None,
    ("500", "mA/V", "LOW NOISE"): None,
}

gain_units = ["pA/V", "nA/V", "uA/V", "mA/V"]
gain_values = ["1", "2", "5", "10", "20", "50", "100", "200", "500"]
gain_modes = ["LOW NOISE", "HIGH BW"]


async def test_preamp_signals(preamp):
    # Check the enums
    await preamp.sensitivity_value.set(SRS570PreAmplifier.SensValue.FIVE)


@pytest.mark.parametrize("gain_mode", gain_modes)
@pytest.mark.parametrize("gain_unit", gain_units)
@pytest.mark.parametrize("gain_value", gain_values)
async def test_preamp_gain_settling(gain_value, gain_unit, gain_mode, mocker, preamp):
    """The SR-570 Pre-amp voltage spikes when changing gain.

    One solution, tested here, is to add a dynamic settling time.

    """
    value_idx = gain_values.index(gain_value)
    unit_idx = gain_units.index(gain_unit)
    settle_time = settling_times[
        (
            gain_value,
            gain_unit,
            gain_mode,
        )
    ]
    # Create and check the device
    assert isinstance(preamp.sensitivity_unit, GainSignal)
    assert isinstance(preamp.sensitivity_value, GainSignal)
    # Set up a mocked sleep function
    sleep_mock = mock.AsyncMock()
    mocker.patch("haven.devices.ion_chamber.asyncio.sleep", sleep_mock)
    # Set the sensitivity based on value
    await preamp.sensitivity_unit.set(gain_unit)
    await preamp.gain_mode.set(gain_mode)
    sleep_mock.reset_mock()
    await preamp.sensitivity_value.set(gain_value)
    # Check that the signal's ``set`` was called with correct arguments
    get_mock_put(preamp.sensitivity_value).assert_called_once_with(
        gain_value,
        wait=True,
    )
    # Check that the settle time was included
    sleep_mock.assert_called_once_with(settle_time)


async def test_preamp_gain_mode_settling(mocker, preamp):
    """The SR-570 Pre-amp also has a low drift mode, whose settling times
    are the same as the low noise mode.

    """
    gain_unit = "pA/V"
    gain_value = "500"
    settle_time = 0.5
    # Set up a mocked sleep function
    sleep_mock = mock.AsyncMock()
    mocker.patch("haven.devices.ion_chamber.asyncio.sleep", sleep_mock)
    # Set the preamp gains
    await preamp.sensitivity_unit.set(gain_unit)
    await preamp.sensitivity_value.set(gain_value)
    sleep_mock.reset_mock()
    await preamp.gain_mode.set("LOW DRIFT")
    # Check that the correct settle_time was used
    sleep_mock.assert_called_once_with(settle_time)


async def test_gain_signals(preamp):
    assert hasattr(preamp, "gain")
    assert hasattr(preamp, "gain_db")
    # Change the preamp settings
    await preamp.sensitivity_value.set("20")
    await preamp.sensitivity_unit.set("uA/V")
    await preamp.offset_value.set("2")
    await preamp.offset_unit.set("uA")
    # Check the gain and gain_db signals
    gain = await preamp.gain.get_value()
    assert gain == pytest.approx(1 / 20e-6)
    gain_db = await preamp.gain_db.get_value()
    assert gain_db == pytest.approx(46.9897)


@pytest.mark.skip(reason="Not sure put complete is needed with ophyd-async")
def test_sensitivity_put_complete():
    """Test the fix for a race condition in the pre-amp EPICS database.

    If the gain is set to 1 mA/V in the IOC, and you try to set it to
    e.g. 200 µA/V, you need to set the unit first then the value since
    "1" is the only valid "mA/V" value:

    ✓ 1 mA/V -> 1 µA/V -> 200 µA/V
    ✗ 1 mA/V -> 200 mA/V (corrects to 1 mA/V) -> 1 µA/V

    Even if the order of ``set`` calls is correct in ophyd, the
    requests may not make it through the calc/transform in the right
    order, so we wind up at the wrong gain.

    Apparently, using put_complete for the sensitivity unit fixes this
    problem, though it's not entirely clear why.

    Regardless, this test checks that put_complete is set on the given
    signal.

    """
    preamp = SRS570PreAmplifier("prefix:", name="preamp")
    put_complete_signals = [
        preamp.sensitivity_unit,
    ]
    for sig in put_complete_signals:
        assert sig._put_complete is True, sig


@pytest.mark.asyncio
async def test_get_gain_level(preamp):
    # Change the preamp settings
    await preamp.sensitivity_value.set("20")
    await preamp.sensitivity_unit.set("uA/V"),
    await preamp.offset_value.set("2"),  # 2 uA/V
    await preamp.offset_unit.set("uA"),
    # Check that the gain level moved
    gain_level = await preamp.gain_level.get_value()
    assert gain_level == 5


@pytest.mark.asyncio
async def test_put_gain_level(preamp):
    # Move the gain level
    await preamp.gain_level.set(15)
    # Check that the preamp sensitivities are moved
    assert await preamp.sensitivity_value.get_value() == "10"
    assert await preamp.sensitivity_unit.get_value() == "nA/V"
    # Check that the preamp sensitivity offsets are moved
    assert await preamp.offset_value.get_value() == "1"
    assert await preamp.offset_unit.get_value() == "nA"
