from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from haven.devices.ion_chamber import IonChamber
from haven.devices.motor import load_motors
from haven.devices.slits import BladeSlits
from haven.instrument import Instrument

haven_dir = Path(__file__).parent.parent.resolve()
toml_file = haven_dir / "iconfig_testing.toml"


@pytest.fixture()
def instrument():
    inst = Instrument(
        {
            "ion_chamber": IonChamber,
            "motors": load_motors,
            "blade_slits": BladeSlits,
        }
    )
    with open(toml_file, mode="tr", encoding="utf-8") as fd:
        inst.parse_toml_file(fd)
    return inst


def test_global_parameters(instrument):
    """Check that we loaded keys that apply to the whole beamline."""
    assert instrument.beamline_name == "SPC Beamline (sector unknown)"
    assert instrument.hardware_is_present == False


def test_validate_missing_params(instrument):
    defn = {
        # "scaler_prefix": "scaler_1:",
        # "scaler_channel": 3,
        # "preamp_prefix": "preamp_1:",
        # "voltmeter_prefix": "labjack_1:",
        # "voltmeter_channel": 1,
        # "counts_per_volt_second": 1e-6,
        # "name": "",
        # "auto_name": None,
    }
    with pytest.raises(Exception):
        instrument.validate_params(defn, IonChamber)


def test_validate_optional_params(instrument):
    defn = {
        "scaler_prefix": "scaler_1:",
        "scaler_channel": 3,
        "preamp_prefix": "preamp_1:",
        "voltmeter_prefix": "labjack_1:",
        "voltmeter_channel": 1,
        "counts_per_volt_second": 1e-6,
        # "name": "",
        # "auto_name": None,
    }
    instrument.validate_params(defn, IonChamber)


def test_validate_wrong_types(instrument):
    defn = {
        "scaler_prefix": "scaler_1:",
        "scaler_channel": "3",
        "preamp_prefix": "preamp_1:",
        "voltmeter_prefix": "labjack_1:",
        "voltmeter_channel": "1",
        "counts_per_volt_second": 1e-6,
        "name": "",
        "auto_name": None,
    }
    with pytest.raises(Exception):
        instrument.validate_params(defn, IonChamber)


async def test_connect(instrument):
    async_devices = [d for d in instrument.devices if hasattr(d, "_connect_task")]
    sync_devices = [d for d in instrument.devices if hasattr(d, "connected")]
    assert len(async_devices) > 0
    assert len(sync_devices) > 0
    # Are devices disconnected to start with?
    assert all([d._connect_task is None for d in async_devices])
    assert all([not d.connected is None for d in sync_devices])
    # Connect the device
    await instrument.connect(mock=True)
    # Are devices connected afterwards?
    # NB: This doesn't actually test the code for threaded devices
    assert all([d._connect_task.done for d in async_devices])


async def test_load(monkeypatch):
    instrument = Instrument({})
    # Mock out the relevant methods to test
    monkeypatch.setattr(instrument, "parse_toml_file", MagicMock())
    monkeypatch.setattr(instrument, "connect", AsyncMock())
    monkeypatch.setenv("HAVEN_CONFIG_FILES", str(toml_file), prepend=False)
    # Execute the loading step
    await instrument.load()
    # Check that the right methods were called
    instrument.parse_toml_file.assert_called_once()
    instrument.connect.assert_called_once_with(mock=True)
