"""
test the SRS DG-645 digital delay device support

Hardware is not available so test with best efforts
"""

import pytest
from ophyd_async.core import TriggerInfo

from haven.devices import SoftGlueFlyerController


@pytest.fixture()
async def soft_glue():
    sg = SoftGlueFlyerController("", name="delay")
    await sg.connect(mock=True)
    return sg


async def test_prepare_softglue_edge_trigger(soft_glue):
    tinfo = TriggerInfo(trigger="EDGE_TRIGGER")
    await soft_glue.prepare(tinfo)
    # Check that the right signals were set up
    assert await soft_glue.pulse_input.signal.get_value() == "pulseIn"
    assert await soft_glue.clock_divider.output_signal.get_value() != "pulseIn"
    # For producing the gate signal
    assert await soft_glue.gate_latch.clock_signal.get_value() == "pulseIn"
    assert await soft_glue.gate_latch.data_signal.get_value() == "1"
    assert await soft_glue.gate_latch.clear_signal.get_value() == "reset*"
    assert await soft_glue.gate_latch.output_signal.get_value() == "gateLatch"
    assert await soft_glue.gate_latch.description.get_value() == "Gate latch"
    # For stopping the triggers/gates once the count is reached
    assert await soft_glue.pulse_counter.clock_signal.get_value() == "pulseIn"
    assert await soft_glue.pulse_counter.load_signal.get_value() == "reset"
    assert await soft_glue.pulse_counter.output_signal.get_value() == "stopTrig"
    assert await soft_glue.pulse_counter.description.get_value() == "Pulse counter"
    assert await soft_glue.pulse_counter.preset_counts.get_value() == 0
    assert await soft_glue.stop_trigger_latch.clock_signal.get_value() == "stopTrig"
    assert await soft_glue.stop_trigger_latch.data_signal.get_value() == "1"
    assert await soft_glue.stop_trigger_latch.clear_signal.get_value() == "reset*"
    assert await soft_glue.stop_trigger_latch.output_signal.get_value() == "blockTrigs"
    assert (
        await soft_glue.stop_trigger_latch.description.get_value()
        == "Block extra triggers"
    )
    assert (
        await soft_glue.output_permitted_gate.inputA_signal.get_value() == "blockTrigs*"
    )
    assert await soft_glue.output_permitted_gate.inputB_signal.get_value() == "pulseIn*"
    assert (
        await soft_glue.output_permitted_gate.output_signal.get_value() == "outPermit"
    )
    assert (
        await soft_glue.output_permitted_gate.description.get_value() == "Output permit"
    )
    # For passing the input pulses back out
    assert await soft_glue.pulse_output.signal.get_value() == "pulseIn"


async def test_prepare_softglue_internal(soft_glue):
    tinfo = TriggerInfo(trigger="INTERNAL")
    await soft_glue.prepare(tinfo)
    # Don't want a trigger input, just internal clocks ticks
    assert await soft_glue.pulse_input.signal.get_value() == ""
    assert await soft_glue.clock_divider.output_signal.get_value() == "pulseIn"
    assert await soft_glue.internal_clock.signal.get_value() == "internClk"
    assert await soft_glue.clock_divider.clock_signal.get_value() == "internClk"
    assert await soft_glue.clock_divider.enable_signal.get_value() == "1"
    assert await soft_glue.clock_divider.reset_signal.get_value() == "reset"
    # Spot check that the gate/trigger outputs also get prepared
    assert await soft_glue.gate_output.and_gate.inputA_signal.get_value() == "outPermit"
    assert (
        await soft_glue.trigger_output.and_gate.inputA_signal.get_value() == "outPermit"
    )


async def test_prepare_softglue_gate_output(soft_glue):
    tinfo = TriggerInfo(trigger="CONSTANT_GATE")
    await soft_glue.gate_output.prepare(tinfo)
    # Don't want a trigger input, just internal clocks ticks
    assert await soft_glue.gate_output.and_gate.inputA_signal.get_value() == "outPermit"
    assert await soft_glue.gate_output.and_gate.inputB_signal.get_value() == "gateLatch"
    assert await soft_glue.gate_output.and_gate.output_signal.get_value() == "gateOut"
    assert await soft_glue.gate_output.output.signal.get_value() == "gateOut"


async def test_prepare_softglue_trigger_output(soft_glue):
    tinfo = TriggerInfo(trigger="EDGE_TRIGGER")
    await soft_glue.trigger_output.prepare(tinfo)
    # Don't want a trigger input, just internal clocks ticks
    assert (
        await soft_glue.trigger_output.and_gate.inputA_signal.get_value() == "outPermit"
    )
    assert (
        await soft_glue.trigger_output.and_gate.inputB_signal.get_value() == "pulseIn"
    )
    assert (
        await soft_glue.trigger_output.and_gate.output_signal.get_value() == "trigOut"
    )
    assert await soft_glue.trigger_output.output.signal.get_value() == "trigOut"


async def test_kickoff_softglue_single_event(soft_glue):
    num_events = 6
    tinfo = TriggerInfo(trigger="INTERNAL", number_of_events=num_events)
    await soft_glue.prepare(tinfo)
    assert await soft_glue.pulse_counter.preset_counts.get_value() == 0
    await soft_glue.kickoff()
    assert await soft_glue.pulse_counter.preset_counts.get_value() == num_events + 1
    assert await soft_glue.reset_buffer.input_signal.get_value() == "1!"
    # Extra kickoffs shouldn't work
    with pytest.raises(RuntimeError):
        await soft_glue.kickoff()


async def test_kickoff_softglue_multiple_events(soft_glue):
    num_events = [6, 9]
    tinfo = TriggerInfo(trigger="INTERNAL", number_of_events=num_events)
    await soft_glue.prepare(tinfo)
    assert await soft_glue.pulse_counter.preset_counts.get_value() == 0
    await soft_glue.kickoff()
    assert await soft_glue.pulse_counter.preset_counts.get_value() == num_events[0] + 1
    assert await soft_glue.reset_buffer.input_signal.get_value() == "1!"
    # Set the reset buffer low to we can check again
    await soft_glue.reset_buffer.input_signal.set("")
    await soft_glue.kickoff()
    assert await soft_glue.pulse_counter.preset_counts.get_value() == num_events[1] + 1
    assert await soft_glue.reset_buffer.input_signal.get_value() == "1!"
