import pytest_asyncio

from haven.devices import SplitIonChamberSet, SRS570PreAmplifier
from haven.devices.shutter import ShutterState
from haven.plans import record_dark_current


@pytest_asyncio.fixture()
async def scaler(sim_registry):
    device = SplitIonChamberSet(prefix="scaler:", name="scaler")
    # device = Counter(prefix="scaler:", channels=[])
    await device.connect(mock=True)
    return device


@pytest_asyncio.fixture()
async def preamp(sim_registry):
    device = SRS570PreAmplifier(prefix="255idz:SR03:", name="preamp")
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
    calibrate_msg = msgs[5]
    assert calibrate_msg.command == "calibrate"
    assert calibrate_msg.obj is scaler
    assert calibrate_msg.kwargs["truth"] == 0
    assert calibrate_msg.kwargs["dial"] == 0
    # Check the shutters get closed
    trigger_msg = msgs[9]
    assert trigger_msg.obj is scaler
    assert "record_dark_current" not in trigger_msg.kwargs
    wait_msg = msgs[10]
    assert wait_msg.command == "wait"
    calibrate_msg = msgs[17]
    assert calibrate_msg.command == "calibrate"
    assert calibrate_msg.obj is scaler
    assert calibrate_msg.kwargs["truth"] == 0


def test_preamp_configuration(shutters, scaler, preamp):
    """Do we get preamps in the configuration metadata."""
    shutter = shutters[0]
    msgs = list(
        record_dark_current(detectors=[scaler], shutters=[shutter], preamps=[preamp])
    )
    read_msgs = [m for m in msgs if m.command == "read"]
    read_objs = [m.obj for m in read_msgs]
    assert preamp in read_objs
