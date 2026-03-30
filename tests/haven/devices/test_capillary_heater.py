import pytest
import pytest_asyncio

from haven.devices import CapillaryHeater


@pytest_asyncio.fixture()
async def heater():
    device = CapillaryHeater("255idc:", name="heater")
    await device.connect(mock=True)
    return device


@pytest.mark.asyncio
async def test_capilary_heater_signals(heater):
    reading = await heater.read()
    assert set(reading.keys()) == {
        "heater-thermocouple-temperature",
        "heater-output-ramp_temperature",
        "heater-output-setpoint",
        "heater-output-voltage",
    }
    hints = heater.hints
    assert set(hints["fields"]) == {
        "heater-thermocouple-temperature",
    }
