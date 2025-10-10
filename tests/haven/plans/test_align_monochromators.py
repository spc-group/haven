import pytest

from haven.devices import AxilonMonochromator, ChannelCutMonochromator
from haven.plans import align_monochromators


@pytest.fixture()
async def primary_mono():
    mono = AxilonMonochromator(prefix="", name="primary_mono")
    await mono.connect(mock=True)
    return mono


@pytest.fixture()
async def secondary_mono():
    mono = ChannelCutMonochromator(
        prefix="", name="secondary_mono", vertical_motor="255idzVME:m1"
    )
    await mono.connect(mock=True)
    return mono


def test_messages(primary_mono, secondary_mono):
    plan = align_monochromators(primary_mono, secondary_mono, primary_offset=10000)
    msgs = list(plan)
    # Check for setting the motor positions
    assert msgs[0].command == "set"
    assert msgs[0].obj == primary_mono.beam_offset
    assert msgs[0].args == (10000,)
    assert msgs[1].command == "set"
