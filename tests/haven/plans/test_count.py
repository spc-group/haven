import pytest_asyncio
from ophyd_async import sim
from ophyd_async.core import TriggerInfo

from haven.plans._count import count


@pytest_asyncio.fixture()
async def detectors():
    pattern_generator = sim.PatternGenerator()
    pdet = sim.SimPointDetector(pattern_generator)
    pdet2 = sim.SimPointDetector(pattern_generator)
    return [pdet, pdet2]


def test_prepare_trigger_info(detectors):
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


def test_metadata(detectors):
    msgs = list(
        count(detectors, num=3, collections_per_event=200, livetime=3.1, delay=0.5)
    )
    md = msgs[2].kwargs
    assert md["plan_name"] == "count"
    assert md["plan_args"]["livetime"] == 3.1
    assert md["plan_args"]["collections_per_event"] == 200
