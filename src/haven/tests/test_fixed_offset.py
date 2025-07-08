import pytest
from bluesky import Msg
from bluesky.utils import ensure_generator

from haven.devices import AxilonMonochromator, ChannelCutMonochromator
from haven.preprocessors import fixed_offset_wrapper
from haven.preprocessors.fixed_offset import beam_offset
from haven.units import ureg


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


def test_beam_offset():
    # Taken from a random configuration at 25-ID-C
    bragg = 67407.927958 * ureg.arcseconds - 2159.15 * ureg.arcseconds
    gap = 4000 * ureg.microns
    offset = 7603.055409 * ureg.microns
    assert beam_offset(bragg, gap=gap).magnitude == pytest.approx(offset.magnitude)


def test_bragg_tracking(primary_mono, secondary_mono):
    bragg = 67407.927958
    input_plan = ensure_generator(
        [
            Msg("set", secondary_mono.bragg, bragg, group="set-43367a", run=None),
            Msg("wait", group="set-43367a", run=None),
        ]
    )
    wrapped = fixed_offset_wrapper(input_plan, primary_mono, secondary_mono)
    next(wrapped)  # Prime the generative coroutine
    primary_beam_offset = 10_000.0
    secondary_beam_offset = 7503.055409
    d_spacing = 1.92  # Å
    gap = 4000.0  # µm
    wrapped.send({secondary_mono.beam_offset.name: {"value": secondary_beam_offset}})
    wrapped.send({"readback": primary_beam_offset})
    wrapped.send({"readback": -2159.15})  # Bragg offset
    wrapped.send({secondary_mono.gap.name: {"value": gap}})
    new_msg = wrapped.send({secondary_mono.d_spacing.name: {"value": d_spacing}})
    assert new_msg.args[0] == pytest.approx(9900)
    other_msgs = list(wrapped)
    assert len(other_msgs) == 2


def test_energy_tracking(primary_mono, secondary_mono):
    # E = hc/2/d/sin(θ)
    #
    # F = 12398.42
    # B = 1.92
    #
    # F/2/B/sin((A+D)/R2S)
    energy = 10057.9
    input_plan = ensure_generator(
        [
            Msg("set", secondary_mono.energy, energy, group="set-43367a", run=None),
            Msg("wait", group="set-43367a", run=None),
        ]
    )
    wrapped = fixed_offset_wrapper(input_plan, primary_mono, secondary_mono)
    next(wrapped)
    primary_beam_offset = 10_000.0
    secondary_beam_offset = 7503.055409
    d_spacing = 1.92  # Å
    gap = 4000.0  # µm
    wrapped.send({secondary_mono.beam_offset.name: {"value": secondary_beam_offset}})
    wrapped.send({"readback": primary_beam_offset})
    wrapped.send({"readback": -2159.15})  # Bragg offset
    wrapped.send({secondary_mono.gap.name: {"value": gap}})
    new_msg = wrapped.send({secondary_mono.d_spacing.name: {"value": d_spacing}})
    assert new_msg.args[0] == pytest.approx(9900)
    other_msgs = list(wrapped)
    assert len(other_msgs) == 2
