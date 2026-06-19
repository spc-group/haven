import pytest_asyncio

from haven.devices import IonChamberScaler
from haven.devices.shutter import ShutterState
from haven.plans import record_dark_current


@pytest_asyncio.fixture()
async def scaler(sim_registry):
    device = IonChamberScaler(prefix="scaler:", ion_chambers={})
    await device.connect(mock=True)
    return device


def test_shutters_get_reset(shutters, ion_chamber):
    shutter = shutters[0]
    msgs = list(record_dark_current(detectors=[ion_chamber], shutters=[shutter]))
    # Check the shutters get closed
    set_shutter_msg = msgs[3]
    assert set_shutter_msg.command == "set"
    assert set_shutter_msg.obj is shutter
    assert set_shutter_msg.args[0] == ShutterState.CLOSED
    # Check the shutters get re-opened
    set_shutter_msg = msgs[-4]
    assert set_shutter_msg.command == "set"
    assert set_shutter_msg.obj is shutter
    assert set_shutter_msg.args[0] == ShutterState.OPEN


def test_messages_for_ion_chamber(shutters, ion_chamber):
    shutter = shutters[0]
    msgs = list(record_dark_current(detectors=[ion_chamber], shutters=[shutter]))
    # Check the shutters get closed
    trigger_msg = msgs[5]
    assert trigger_msg.obj is ion_chamber
    assert trigger_msg.kwargs["record_dark_current"] is True


def test_messages(shutters, scaler):
    shutter = shutters[0]
    msgs = list(record_dark_current(detectors=[scaler], shutters=[shutter]))
    # Check the shutters get closed
    trigger_msg = msgs[8]
    assert trigger_msg.obj is scaler
    assert "record_dark_current" not in trigger_msg.kwargs
    wait_msg = msgs[9]
    assert wait_msg.command == "wait"
    calibrate_msg = msgs[16]
    assert calibrate_msg.command == "calibrate"
    assert calibrate_msg.obj is scaler
    assert calibrate_msg.kwargs["truth"] == 0
