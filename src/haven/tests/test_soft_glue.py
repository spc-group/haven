import pytest

from haven.devices.soft_glue import SoftGlueZynq


@pytest.fixture()
async def soft_glue():
    sg = SoftGlueZynq(
        prefix="255idzMZ1:SG:",
        name="softglue",
        # Only one of each module, to make testing easier
        and_gates=[0],
        or_gates=[0],
        xor_gates=[0],
        buffers=[0],
        latches=[0],
        multiplexers=[0],
        demultiplexers=[0],
        up_counters=[0],
        down_counters=[0],
        up_down_counters=[0],
        dividers=[0],
        quadrature_decoders=[0],
        gate_and_delay_generators=[0],
        inputs=[0],
        outputs=[0],
    )
    await sg.connect(mock=True)
    return sg


async def test_soft_glue_signals(soft_glue):
    # Shouldn't really be any readable signals by default
    read_names = []
    read_attrs = (await soft_glue.describe()).keys()
    assert sorted(read_attrs) == read_names

    # Check configuration signals
    cfg_names = [
        "softglue-and_gates-0-inputA_signal",
        "softglue-and_gates-0-inputB_signal",
        "softglue-and_gates-0-output_signal",
        "softglue-and_gates-0-description",
        "softglue-or_gates-0-inputA_signal",
        "softglue-or_gates-0-inputB_signal",
        "softglue-or_gates-0-output_signal",
        "softglue-or_gates-0-description",
        "softglue-xor_gates-0-inputA_signal",
        "softglue-xor_gates-0-inputB_signal",
        "softglue-xor_gates-0-output_signal",
        "softglue-xor_gates-0-description",
        "softglue-buffers-0-description",
        "softglue-buffers-0-input_signal",
        "softglue-buffers-0-output_signal",
        "softglue-clock_10MHz-signal",
        "softglue-clock_20MHz-signal",
        "softglue-clock_50MHz-signal",
        "softglue-clock_variable-signal",
        "softglue-latches-0-clear_signal",
        "softglue-latches-0-clock_signal",
        "softglue-latches-0-data_signal",
        "softglue-latches-0-description",
        "softglue-latches-0-output_signal",
        "softglue-latches-0-set_signal",
        "softglue-multiplexers-0-description",
        "softglue-multiplexers-0-inputA_signal",
        "softglue-multiplexers-0-inputB_signal",
        "softglue-multiplexers-0-output_signal",
        "softglue-multiplexers-0-select_signal",
        "softglue-demultiplexers-0-description",
        "softglue-demultiplexers-0-input_signal",
        "softglue-demultiplexers-0-outputA_signal",
        "softglue-demultiplexers-0-outputB_signal",
        "softglue-demultiplexers-0-select_signal",
        "softglue-up_counters-0-clock_signal",
        "softglue-up_counters-0-clear_signal",
        "softglue-up_counters-0-description",
        "softglue-up_counters-0-enable_signal",
        "softglue-down_counters-0-clock_signal",
        "softglue-down_counters-0-description",
        "softglue-down_counters-0-enable_signal",
        "softglue-down_counters-0-output_signal",
        "softglue-down_counters-0-preset_counts",
        "softglue-down_counters-0-load_signal",
        "softglue-up_down_counters-0-clear_signal",
        "softglue-up_down_counters-0-clock_signal",
        "softglue-up_down_counters-0-description",
        "softglue-up_down_counters-0-direction_signal",
        "softglue-up_down_counters-0-enable_signal",
        "softglue-up_down_counters-0-load_signal",
        "softglue-up_down_counters-0-output_signal",
        "softglue-up_down_counters-0-preset_counts",
        "softglue-dividers-0-clock_signal",
        "softglue-dividers-0-description",
        "softglue-dividers-0-divisor",
        "softglue-dividers-0-enable_signal",
        "softglue-dividers-0-output_signal",
        "softglue-dividers-0-reset_signal",
        "softglue-quadrature_decoders-0-clock_signal",
        "softglue-quadrature_decoders-0-description",
        "softglue-quadrature_decoders-0-direction_signal",
        "softglue-quadrature_decoders-0-inputA_signal",
        "softglue-quadrature_decoders-0-inputB_signal",
        "softglue-quadrature_decoders-0-miss_clear_signal",
        "softglue-quadrature_decoders-0-miss_signal",
        "softglue-quadrature_decoders-0-step_signal",
        "softglue-gate_and_delay_generators-0-clock_signal",
        "softglue-gate_and_delay_generators-0-delay",
        "softglue-gate_and_delay_generators-0-description",
        "softglue-gate_and_delay_generators-0-input_signal",
        "softglue-gate_and_delay_generators-0-output_signal",
        "softglue-gate_and_delay_generators-0-width",
        "softglue-frequency_counter-description",
        "softglue-frequency_counter-input_signal",
        "softglue-inputs-0-description",
        "softglue-inputs-0-signal",
        "softglue-outputs-0-description",
        "softglue-outputs-0-signal",
    ]
    cfg_attrs = (await soft_glue.describe_configuration()).keys()
    assert sorted(cfg_names) == sorted(cfg_attrs)
