"""Tests for customized versions of the standard Bluesky plans."""

import pytest
import pytest_asyncio
from ophyd_async import sim
from ophyd_async.core import TriggerInfo

from haven.devices import IonChamber, Xspress3Detector
from haven.plans._bluesky import count, rel_scan, scan


@pytest_asyncio.fixture()
async def devices():
    pattern_generator = sim.PatternGenerator()
    xspress = Xspress3Detector("", sensor_material="Ge", sensor_thickness_mm=1)
    ion_chamber = IonChamber(
        scaler_prefix="",
        scaler_channel=1,
        preamp_prefix="",
        voltmeter_prefix="",
        voltmeter_channel=1,
        counts_per_volt_second=1e6,
    )
    stage = sim.SimStage(pattern_generator)
    return [stage, xspress, ion_chamber]


@pytest.mark.parametrize("plan_func", [scan, rel_scan])
def test_line_scan_prepares_trigger_info(devices, plan_func):
    stage, *detectors = devices
    msgs = list(
        plan_func(
            detectors, stage.x, -10, 10, num=3, collections_per_event=200, livetime=3.1
        )
    )
    prepare_msg = msgs[4]
    assert prepare_msg.command == "prepare"
    assert prepare_msg.obj is detectors[0]
    assert prepare_msg.args == (
        TriggerInfo(
            number_of_events=1,
            collections_per_event=200,
            livetime=3.1,
        ),
    )
    group = prepare_msg.kwargs["group"]
    prepare_msg = msgs[5]
    assert prepare_msg.command == "prepare"
    assert prepare_msg.obj is detectors[1]
    assert prepare_msg.args == (
        TriggerInfo(
            number_of_events=1,
            collections_per_event=200,
            livetime=3.1,
        ),
    )
    assert prepare_msg.kwargs == {"group": group}
    # Make sure we wait for the prepares to be done
    wait_msg = msgs[6]
    assert wait_msg.command == "wait"
    assert wait_msg.kwargs["group"] == group
    # Ensure we only prepare each device once
    all_prep_msgs = [msg for msg in msgs if msg.command == "prepare"]
    assert len(all_prep_msgs) == len(detectors)


@pytest.mark.parametrize("plan_func", [scan, rel_scan])
def test_line_scan_metadata(devices, plan_func):
    stage, *detectors = devices
    msgs = list(
        plan_func(
            detectors, stage.x, -10, 10, num=3, collections_per_event=200, livetime=3.1
        )
    )
    md = msgs[3].kwargs
    assert md["plan_name"] == plan_func.__name__
    assert md["plan_args"]["livetime"] == 3.1
    assert md["plan_args"]["collections_per_event"] == 200


def test_count_prepares_trigger_info(devices):
    _, *detectors = devices
    msgs = list(
        count(detectors, num=3, collections_per_event=200, livetime=3.1, delay=0.5)
    )
    prepare_msg = msgs[4]
    assert prepare_msg.command == "prepare"
    assert prepare_msg.obj is detectors[0]
    assert prepare_msg.args == (
        TriggerInfo(
            number_of_events=1,
            collections_per_event=200,
            livetime=3.1,
        ),
    )
    group = prepare_msg.kwargs["group"]
    prepare_msg = msgs[5]
    assert prepare_msg.command == "prepare"
    assert prepare_msg.obj is detectors[1]
    assert prepare_msg.args == (
        TriggerInfo(
            number_of_events=1,
            collections_per_event=200,
            livetime=3.1,
        ),
    )
    assert prepare_msg.kwargs == {"group": group}
    # Make sure we wait for the prepares to be done
    wait_msg = msgs[6]
    assert wait_msg.command == "wait"
    assert wait_msg.kwargs["group"] == group
    # Ensure we only prepare each device once
    all_prep_msgs = [msg for msg in msgs if msg.command == "prepare"]
    assert len(all_prep_msgs) == len(detectors)


def test_count_metadata(devices):
    _, *detectors = devices
    msgs = list(
        count(detectors, num=3, collections_per_event=200, livetime=3.1, delay=0.5)
    )
    md = msgs[2].kwargs
    assert md["plan_name"] == "count"
    assert md["plan_args"]["livetime"] == 3.1
    assert md["plan_args"]["collections_per_event"] == 200
