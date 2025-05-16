from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from haven.devices import IonChamber, Robot, load_motors, Motor
from haven.instrument import Instrument, make_devices

haven_dir = Path(__file__).parent.parent.resolve()
toml_file = haven_dir / "iconfig_testing.toml"


@pytest.fixture()
def instrument():
    inst = Instrument(
        {
            "ion_chamber": IonChamber,
            "motors": load_motors,
            "robot": Robot,
        }
    )
    with open(toml_file, mode="tr", encoding="utf-8") as fd:
        inst.parse_toml_file(fd)
    return inst


def test_load(monkeypatch):
    instrument = Instrument({})
    # Mock out the relevant methods to test
    monkeypatch.setattr(instrument, "parse_toml_file", MagicMock())
    monkeypatch.setattr(instrument, "connect", AsyncMock(return_value=([], [])))
    monkeypatch.setenv("HAVEN_CONFIG_FILES", str(toml_file), prepend=False)
    # Execute the loading step
    instrument.load(toml_file)
    # Check that the right methods were called
    instrument.parse_toml_file.assert_called_once()


def test_make_devices():
    m1, m2 = make_devices(Motor)(
        m1="255idzVME:m1",
        m2="255idzVME:m2",
    )
    assert m1.name == "m1"
    assert m1.user_readback.source == "ca://255idzVME:m1.RBV"
    assert m2.name == "m2"
    assert m2.user_readback.source == "ca://255idzVME:m2.RBV"
