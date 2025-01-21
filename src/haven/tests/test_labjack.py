"""Test the Labjack T-series data acquisition device support

Hardware is not available so test with best efforts

"""

import pytest

from haven.devices.labjack import (
    AnalogInput,
    AnalogOutput,
    DigitalIO,
    LabJackBase,
    LabJackT4,
    LabJackT7,
    LabJackT7Pro,
    LabJackT8,
    WaveformDigitizer,
    WaveformGenerator,
)

PV_PREFIX = "255idc:LJ_T7:"


@pytest.fixture()
async def labjack():
    lj = LabJackBase(PV_PREFIX, name="labjack", analog_outputs=range(2))
    await lj.connect(mock=True)
    return lj


@pytest.mark.asyncio
async def test_base_signals_device(labjack):
    """Test signals shared by all labjack devices."""
    cfg_names = {
        "labjack-model_name",
        "labjack-firmware_version",
        "labjack-serial_number",
        "labjack-device_temperature",
        "labjack-ljm_version",
        "labjack-driver_version",
        "labjack-last_error_message",
        "labjack-poll_sleep_ms",
        "labjack-analog_in_settling_time_all",
        "labjack-analog_in_resolution_all",
        "labjack-analog_in_sampling_rate",
        "labjack-analog_outputs-0-description",
        "labjack-analog_outputs-0-desired_output_location",
        "labjack-analog_outputs-0-device_type",
        "labjack-analog_outputs-0-output_link",
        "labjack-analog_outputs-0-output_mode_select",
        "labjack-analog_outputs-0-scanning_rate",
        "labjack-analog_outputs-1-description",
        "labjack-analog_outputs-1-desired_output_location",
        "labjack-analog_outputs-1-device_type",
        "labjack-analog_outputs-1-output_link",
        "labjack-analog_outputs-1-output_mode_select",
        "labjack-analog_outputs-1-scanning_rate",
    }
    desc = await labjack.describe_configuration()
    assert set(desc.keys()) == cfg_names


ai_params = [
    # (model, number of analog inputs)
    (LabJackT4, 12),
    (LabJackT7, 14),
    (LabJackT7Pro, 14),
    (LabJackT8, 8),
]


@pytest.mark.parametrize("LabJackDevice,num_ais", ai_params)
async def test_analog_inputs(LabJackDevice, num_ais):
    """Test analog inputs for different device types."""
    device = LabJackDevice(PV_PREFIX, name="labjack_T")
    await device.connect(mock=True)
    assert hasattr(device, "analog_inputs")
    # Check that the individual AI devices were created
    for n in range(num_ais):
        assert n in device.analog_inputs.keys()
        ai = device.analog_inputs[n]
        assert isinstance(ai, AnalogInput)
    # Make sure there aren't any extra analog inputs
    assert num_ais not in device.analog_inputs.keys()
    # Check read attrs
    read_attrs = ["final_value"]
    description = await device.describe()
    for n in range(num_ais):
        for attr in read_attrs:
            full_attr = f"{device.name}-analog_inputs-{n}-{attr}"
            assert full_attr in description.keys()
    # Check configuration attrs
    cfg_attrs = [
        "differential",
        "high",
        "low",
        "temperature_units",
        "resolution",
        "range",
        "mode",
        "enable",
    ]
    description = await device.describe_configuration()
    for n in range(num_ais):
        for attr in cfg_attrs:
            full_attr = f"{device.name}-analog_inputs-{n}-{attr}"
            assert full_attr in description.keys()


ao_params = [
    # (model, number of analog outputs)
    (LabJackT4, 2),
    (LabJackT7, 2),
    (LabJackT7Pro, 2),
    (LabJackT8, 2),
]


@pytest.mark.parametrize("LabJackDevice,num_aos", ao_params)
async def test_analog_outputs(LabJackDevice, num_aos):
    """Test analog inputs for different device types."""
    device = LabJackDevice(PV_PREFIX, name="labjack_T")
    await device.connect(mock=True)
    assert hasattr(device, "analog_outputs")
    # Check that the individual AI devices were created
    for n in range(num_aos):
        assert n in device.analog_outputs.keys()
        ai = device.analog_outputs[n]
        assert isinstance(ai, AnalogOutput)
    # Check read attrs
    read_attrs = ["desired_value"]
    description = await device.describe()
    for n in range(num_aos):
        for attr in read_attrs:
            full_attr = f"{device.name}-analog_outputs-{n}-{attr}"
            assert full_attr in description.keys()
    # Check configuration attrs
    cfg_attrs = ["output_mode_select"]
    description = await device.describe_configuration()
    for n in range(num_aos):
        for attr in cfg_attrs:
            full_attr = f"{device.name}-analog_outputs-{n}-{attr}"
            assert full_attr in description.keys()
    # Check hinted attrs
    hinted_attrs = ["readback_value"]
    for n in range(num_aos):
        for attr in hinted_attrs:
            full_attr = f"{device.name}-analog_outputs-{n}-{attr}"
            assert full_attr in device.hints["fields"]


dio_params = [
    # (model, number of digital I/Os)
    (LabJackT4, 16),
    (LabJackT7, 23),
    (LabJackT7Pro, 23),
    (LabJackT8, 20),
]


@pytest.mark.parametrize("LabJackDevice,num_dios", dio_params)
async def test_digital_ios(LabJackDevice, num_dios):
    """Test analog inputs for different device types."""
    device = LabJackDevice(PV_PREFIX, name="labjack_T")
    await device.connect(mock=True)
    assert hasattr(device, "digital_ios")
    # Check that the individual digital I/O devices were created
    for n in range(num_dios):
        assert n in device.digital_ios.keys()
        dio = device.digital_ios[n]
        assert isinstance(dio, DigitalIO)
    # Check read attrs
    read_attrs = ["output-desired_value", "input-final_value"]
    description = await device.describe()
    for n in range(num_dios):
        for attr in read_attrs:
            full_attr = f"{device.name}-digital_ios-{n}-{attr}"
            assert full_attr in description.keys()
    # Check configuration attrs
    cfg_attrs = ["direction"]
    description = await device.describe_configuration()
    for n in range(num_dios):
        for attr in cfg_attrs:
            full_attr = f"{device.name}-digital_ios-{n}-{attr}"
            assert full_attr in description.keys()
    # # Check hinted attrs
    # hinted_attrs = ["output-readback_value"]
    # for n in range(num_dios):
    #     for attr in hinted_attrs:
    #         full_attr = f"{device.name}-digital_ios-{n}-{attr}"
    #         assert full_attr in device.hints["fields"]


@pytest.mark.parametrize("LabJackDevice,num_dios", dio_params)
async def test_digital_words(LabJackDevice, num_dios):
    """Test analog inputs for different device types."""
    device = LabJackDevice(PV_PREFIX, name="labjack_T")
    await device.connect(mock=True)
    # Check that the individual digital word outputs were created
    assert hasattr(device, "dio")
    assert hasattr(device, "fio")
    assert hasattr(device, "eio")
    assert hasattr(device, "cio")
    assert hasattr(device, "mio")
    # Check read attrs
    read_attrs = ["dio", "eio", "fio", "mio", "cio"]
    description = await device.describe()
    for attr in read_attrs:
        assert f"{device.name}-{attr}" in description.keys()


async def test_waveform_digitizer():
    digitizer = WaveformDigitizer("LabJackT7_1:", name="labjack")
    await digitizer.connect(mock=True)
    # Check read attrs
    read_attrs = ["timebase_waveform", "dwell_actual", "total_time"]
    description = await digitizer.describe()
    for attr in read_attrs:
        assert f"{digitizer.name}-{attr}" in description.keys()
    # Check read attrs
    cfg_attrs = [
        "num_points",
        "first_chan",
        "num_chans",
        "dwell_time",
        "resolution",
        "settling_time",
    ]
    description = await digitizer.describe_configuration()
    for attr in cfg_attrs:
        assert f"{digitizer.name}-{attr}" in description.keys()


@pytest.mark.parametrize("LabJackDevice,num_ais", ai_params)
async def test_waveform_digitizer_waveforms(LabJackDevice, num_ais):
    """Verify that the waveform digitizer is created for each LabJack."""
    device = LabJackDevice(PV_PREFIX, name="labjack_T")
    await device.connect(mock=True)
    assert hasattr(device, "waveform_digitizer")
    digitizer = device.waveform_digitizer
    assert hasattr(digitizer, "waveforms")


async def test_waveform_generator():
    generator = WaveformGenerator("LabJackT7_1:", name="labjack")
    await generator.connect(mock=True)
    # Check read attrs
    read_attrs = [
        "frequency",
        "dwell",
        "dwell_actual",
        "total_time",
        "user_time_waveform",
        "internal_time_waveform",
    ]
    description = await generator.describe()
    for attr in read_attrs:
        assert f"{generator.name}-{attr}" in description.keys()
    # Check read attrs
    cfg_attrs = [
        "external_trigger",
        "external_clock",
        "continuous",
        "num_points",
        "user_waveform_0",
        "enable_0",
        "type_0",
        "pulse_width_0",
        "amplitude_0",
        "offset_0",
        "user_waveform_1",
        "enable_1",
        "type_1",
        "pulse_width_1",
        "amplitude_1",
        "offset_1",
    ]
    description = await generator.describe_configuration()
    for attr in cfg_attrs:
        assert f"{generator.name}-{attr}" in description.keys()
