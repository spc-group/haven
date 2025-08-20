"""
test the SRS DG-645 digital delay device support

Hardware is not available so test with best efforts
"""

import pytest
from ophyd_async.core import DetectorTrigger, TriggerInfo
from ophyd_async.testing import assert_value

from haven.devices import delay


@pytest.fixture()
async def dg645():
    dg645 = delay.DG645Delay("", name="delay")
    await dg645.connect(mock=True)
    return dg645


async def test_dg645_device(dg645):
    read_names = []
    read_attrs = (await dg645.describe()).keys()
    assert sorted(read_attrs) == read_names

    cfg_names = [
        "delay-burst_config",
        "delay-burst_count",
        "delay-burst_delay",
        "delay-burst_mode",
        "delay-burst_period",
        "delay-channel_A-reference",
        "delay-channel_A-delay",
        "delay-channel_B-reference",
        "delay-channel_B-delay",
        "delay-channel_C-reference",
        "delay-channel_C-delay",
        "delay-channel_D-reference",
        "delay-channel_D-delay",
        "delay-channel_E-reference",
        "delay-channel_E-delay",
        "delay-channel_F-reference",
        "delay-channel_F-delay",
        "delay-channel_G-reference",
        "delay-channel_G-delay",
        "delay-channel_H-reference",
        "delay-channel_H-delay",
        "delay-device_id",
        "delay-label",
        "delay-output_AB-amplitude",
        "delay-output_AB-offset",
        "delay-output_AB-polarity",
        "delay-output_AB-trigger_phase",
        "delay-output_AB-trigger_prescale",
        "delay-output_CD-amplitude",
        "delay-output_CD-offset",
        "delay-output_CD-polarity",
        "delay-output_CD-trigger_phase",
        "delay-output_CD-trigger_prescale",
        "delay-output_EF-amplitude",
        "delay-output_EF-offset",
        "delay-output_EF-polarity",
        "delay-output_EF-trigger_phase",
        "delay-output_EF-trigger_prescale",
        "delay-output_GH-amplitude",
        "delay-output_GH-offset",
        "delay-output_GH-polarity",
        "delay-output_GH-trigger_phase",
        "delay-output_GH-trigger_prescale",
        "delay-output_T0-amplitude",
        "delay-output_T0-offset",
        "delay-output_T0-polarity",
        "delay-trigger_advanced_mode",
        "delay-trigger_holdoff",
        "delay-trigger_inhibit",
        "delay-trigger_level",
        "delay-trigger_prescale",
        "delay-trigger_rate",
        "delay-trigger_source",
    ]
    cfg_attrs = (await dg645.describe_configuration()).keys()
    assert sorted(cfg_attrs) == sorted(cfg_names)

    # List all the components
    cpt_names = [
        "delay-autoip_state",
        "delay-bare_socket_state",
        "delay-burst_config",
        "delay-burst_count",
        "delay-burst_delay",
        "delay-burst_mode",
        "delay-burst_period",
        "delay-channel_A",
        "delay-channel_B",
        "delay-channel_C",
        "delay-channel_D",
        "delay-channel_E",
        "delay-channel_F",
        "delay-channel_G",
        "delay-channel_H",
        "delay-clear_error",
        "delay-device_id",
        "delay-dhcp_state",
        "delay-gateway",
        "delay-goto_local",
        "delay-goto_remote",
        "delay-gpib_address",
        "delay-gpib_state",
        "delay-ip_address",
        "delay-label",
        "delay-lan_state",
        "delay-mac_address",
        "delay-network_mask",
        "delay-output_AB",
        "delay-output_CD",
        "delay-output_EF",
        "delay-output_GH",
        "delay-output_T0",
        "delay-reset",
        "delay-reset_gpib",
        "delay-reset_lan",
        "delay-reset_serial",
        "delay-serial_baud",
        "delay-serial_state",
        "delay-static_ip_state",
        "delay-status",
        "delay-status_checking",
        "delay-telnet_state",
        "delay-trigger_advanced_mode",
        "delay-trigger_holdoff",
        "delay-trigger_inhibit",
        "delay-trigger_level",
        "delay-trigger_prescale",
        "delay-trigger_rate",
        "delay-trigger_source",
        "delay-vxi11_state",
    ]
    child_names = [child.name for attr, child in dg645.children()]
    assert sorted(child_names) == sorted(cpt_names)


async def test_prepare_delay_internal(dg645):
    tinfo = TriggerInfo()
    await dg645.prepare(tinfo)
    await assert_value(dg645.trigger_source, "Internal")


async def test_prepare_delay_edge_trigger(dg645):
    tinfo = TriggerInfo(
        trigger=DetectorTrigger.EDGE_TRIGGER,
    )
    await dg645.prepare(tinfo)
    await assert_value(dg645.trigger_source, "Ext rising edge")


async def test_prepare_output_edge(dg645):
    tinfo = TriggerInfo(
        trigger=DetectorTrigger.EDGE_TRIGGER,
    )
    output = dg645.output_AB
    await output.prepare(tinfo)
    await assert_value(dg645.channel_A.reference, "T0")
    await assert_value(dg645.channel_A.delay, 0)
    await assert_value(dg645.channel_B.reference, "T0")
    await assert_value(dg645.channel_B.delay, 1e-8)


async def test_prepare_output_edge(dg645):
    tinfo = TriggerInfo(
        trigger=DetectorTrigger.CONSTANT_GATE, livetime=1.3, deadtime=0.1
    )
    output = dg645.output_AB
    await output.prepare(tinfo)
    await assert_value(dg645.channel_A.reference, "T0")
    await assert_value(dg645.channel_A.delay, 0)
    await assert_value(dg645.channel_B.reference, "T0")
    await assert_value(dg645.channel_B.delay, 1.2)


@pytest.fixture()
async def soft_glue():
    sg = delay.SoftGlueDelay("", name="delay")
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
    assert await soft_glue.stop_trigger_latch.description.get_value() == "Block extra triggers"
    assert await soft_glue.output_permitted_gate.inputA_signal.get_value() == "blockTrigs*"
    assert await soft_glue.output_permitted_gate.inputB_signal.get_value() == "pulseIn*"
    assert await soft_glue.output_permitted_gate.output_signal.get_value() == "outPermit"
    assert await soft_glue.output_permitted_gate.description.get_value() == "Output permit"
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
    assert await soft_glue.trigger_output.and_gate.inputA_signal.get_value() == "outPermit"
    assert await soft_glue.trigger_output.and_gate.inputB_signal.get_value() == "pulseIn"
    assert await soft_glue.trigger_output.and_gate.output_signal.get_value() == "trigOut"
    assert await soft_glue.trigger_output.output.signal.get_value() == "trigOut"
    
async def test_kickoff_softglue_single_event(soft_glue):
    tinfo = TriggerInfo(trigger="INTERNAL", number_of_events=6)
    await soft_glue.prepare(tinfo)
    assert await soft_glue.pulse_counter.preset_counts.get_value() == 0
    await soft_glue.kickoff()
    assert await soft_glue.pulse_counter.preset_counts.get_value() == 6
    assert await soft_glue.reset_buffer.input_signal.get_value() == "1!"
    # Extra kickoffs shouldn't work
    with pytest.raises(RuntimeError):
        await soft_glue.kickoff()


async def test_kickoff_softglue_multiple_events(soft_glue):
    tinfo = TriggerInfo(trigger="INTERNAL", number_of_events=[6, 9])
    await soft_glue.prepare(tinfo)
    assert await soft_glue.pulse_counter.preset_counts.get_value() == 0
    await soft_glue.kickoff()
    assert await soft_glue.pulse_counter.preset_counts.get_value() == 6
    assert await soft_glue.reset_buffer.input_signal.get_value() == "1!"
    # Set the reset buffer low to we can check again
    await soft_glue.reset_buffer.input_signal.set("")
    await soft_glue.kickoff()
    assert await soft_glue.pulse_counter.preset_counts.get_value() == 9
    assert await soft_glue.reset_buffer.input_signal.get_value() == "1!"
