from pathlib import Path

import pytest

from haven.devices.ion_chamber import IonChamber
from haven.instrument import Instrument

haven_dir = Path(__file__).parent.parent.resolve()
toml_file = haven_dir / "iconfig_testing.toml"


@pytest.fixture()
def instrument():
    inst = Instrument({"ion_chamber": IonChamber})
    return inst


def test_parse_toml_file(instrument):
    with open(toml_file, mode="tr", encoding="utf-8") as fd:
        devices = instrument.parse_toml_file(fd)
        assert len(devices) > 0
        I0 = devices[0]
        assert isinstance(I0, IonChamber)


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
