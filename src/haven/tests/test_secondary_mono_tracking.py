import math

import pytest
from bluesky import Msg
from bluesky.utils import ensure_generator

from haven.devices import AxilonMonochromator, ChannelCutMonochromator
from haven.preprocessors import secondary_mono_tracking_wrapper
from haven.preprocessors.secondary_mono_tracking import beam_offset


@pytest.fixture()
async def primary_mono():
    mono = AxilonMonochromator(prefix="", name="primary_mono")
    await mono.connect(mock=True)
    return mono


@pytest.fixture()
async def secondary_mono():
    mono = ChannelCutMonochromator(prefix="", name="secondary_mono")
    await mono.connect(mock=True)
    return mono


def test_beam_offset():
    # Taken from a random configuration at 25-ID-C
    bragg = 67407.927958 - 2159.15
    assert beam_offset(bragg, gap=4000) == pytest.approx(7603.055409)


def test_bragg_tracking(primary_mono, secondary_mono):
    bragg = 67407.927958
    input_plan = ensure_generator(
        [
            Msg("set", secondary_mono.bragg, bragg, group="set-43367a", run=None),
            Msg("wait", group="set-43367a", run=None),
        ]
    )
    wrapped = secondary_mono_tracking_wrapper(input_plan, secondary_mono, primary_mono)
    next(wrapped)
    primary_beam_offset = 10_000.0
    secondary_beam_offset = 7503.055409
    gap = 4000.0  # µm
    wrapped.send({secondary_mono.beam_offset.name: {"value": secondary_beam_offset}})
    wrapped.send({"readback": primary_beam_offset})
    wrapped.send({"readback": -2159.15})  # Bragg offset
    new_msg = wrapped.send({secondary_mono.gap.name: {"value": gap}})
    assert new_msg.args[0] == pytest.approx(9900)
    other_msgs = list(wrapped)
    assert len(other_msgs) == 2


def test_energy_tracking():
    assert False
