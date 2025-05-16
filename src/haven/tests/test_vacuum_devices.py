import pytest

from haven.devices import PumpController, TelevacIonGauge


@pytest.fixture()
async def qpc_pump():
    device = PumpController(prefix="255idVac:qpc99z:", name="downstream_ion_pump")
    await device.connect(mock=True)
    return device


@pytest.fixture()
async def televac():
    device = TelevacIonGauge(prefix="255idVac:VSA6", name="outdoor_ion_gauge")
    await device.connect(mock=True)
    return device


def test_qpc_signals(qpc_pump):
    assert qpc_pump.pressure.source == "mock+ca://255idVac:qpc99z:Pressure"
    assert qpc_pump.size.source == "mock+ca://255idVac:qpc99z:PumpSize"
    assert qpc_pump.current.source == "mock+ca://255idVac:qpc99z:Current"
    assert qpc_pump.voltage.source == "mock+ca://255idVac:qpc99z:Voltage"
    assert qpc_pump.status.source == "mock+ca://255idVac:qpc99z:Status"
    assert qpc_pump.description.source == "mock+ca://255idVac:qpc99z:Pump26Name"
    assert qpc_pump.model.source == "mock+ca://255idVac:qpc99z:Model"


async def test_qpc_reading(qpc_pump):
    reading = await qpc_pump.read()
    expected_keys = {
        "downstream_ion_pump-pressure",
        "downstream_ion_pump-current",
        "downstream_ion_pump-voltage",
        "downstream_ion_pump-status",
    }
    assert set(reading.keys()) == expected_keys


async def test_qpc_config(qpc_pump):
    config = await qpc_pump.read_configuration()
    expected_keys = {
        "downstream_ion_pump-size",
        "downstream_ion_pump-description",
        "downstream_ion_pump-model",
    }
    assert set(config.keys()) == expected_keys


def test_televac_signals(televac):
    assert televac.pressure.source == "mock+ca://255idVac:VSA6.VAL" 
    assert televac.device_type.source == "mock+ca://255idVac:VSA6.TYPE"


async def test_televac_reading(televac):
    reading = await televac.read()
    expected_keys = {
        "outdoor_ion_gauge-pressure",
    }
    assert set(reading.keys()) == expected_keys


async def test_televac_config(televac):
    config = await televac.read_configuration()
    expected_keys = {
        "outdoor_ion_gauge-device_type"
    }
    assert set(config.keys()) == expected_keys
