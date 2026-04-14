import pytest
from ophyd_async.core import TriggerInfo, set_mock_value

from haven.devices.detectors.usb_counter import USBCounter


@pytest.fixture()
def counter(sim_registry):
    counter = USBCounter(
        prefix="255idc:USBCTR0:", channels=range(1, 8), name="jetstream_ion_chambers"
    )
    return counter


def test_signals(counter):
    # Global device signals
    assert counter.driver.model.source == "ca://255idc:USBCTR0:ModelName"
    assert counter.driver.model_number.source == "ca://255idc:USBCTR0:ModelNumber"
    assert counter.driver.unique_id.source == "ca://255idc:USBCTR0:UniqueID"
    assert (
        counter.driver.firmware_version.source == "ca://255idc:USBCTR0:FirmwareVersion"
    )
    assert counter.driver.ul_version.source == "ca://255idc:USBCTR0:ULVersion"
    assert counter.driver.driver_version.source == "ca://255idc:USBCTR0:DriverVersion"
    # Clocks/pulse generators
    generator = counter.driver.pulse_generators[0]
    assert generator.frequency.source == "ca://255idc:USBCTR0:PulseGen1Frequency_RBV"
    assert generator.period.source == "ca://255idc:USBCTR0:PulseGen1Period_RBV"
    assert generator.duty_cycle.source == "ca://255idc:USBCTR0:PulseGen1DutyCycle_RBV"
    assert generator.pulse_width.source == "ca://255idc:USBCTR0:PulseGen1Width_RBV"
    assert generator.running.source == "ca://255idc:USBCTR0:PulseGen1Run"
    # Multi-channel scaler signals
    assert counter.driver.start_all.source == "ca://255idc:USBCTR0:MCS:StartAll"
    assert counter.driver.stop_all.source == "ca://255idc:USBCTR0:MCS:StopAll"
    assert counter.driver.erase_all.source == "ca://255idc:USBCTR0:MCS:EraseAll"
    assert counter.driver.erase_start.source == "ca://255idc:USBCTR0:MCS:EraseStart"
    assert counter.driver.preset_time.source == "ca://255idc:USBCTR0:MCS:PresetReal"
    assert counter.driver.dwell_time.source == "ca://255idc:USBCTR0:MCS:Dwell_RBV"
    assert counter.driver.acquiring.source == "ca://255idc:USBCTR0:MCS:Acquiring"
    assert counter.driver.elapsed_time.source == "ca://255idc:USBCTR0:MCS:ElapsedReal"
    assert (
        counter.driver.current_channel.source
        == "ca://255idc:USBCTR0:MCS:CurrentChannel"
    )
    assert counter.driver.prescale.source == "ca://255idc:USBCTR0:MCS:Prescale"
    assert (
        counter.driver.channel_advance_source.source
        == "ca://255idc:USBCTR0:MCS:ChannelAdvance"
    )
    assert (
        counter.driver.num_channels_max.source == "ca://255idc:USBCTR0:MCS:MaxChannels"
    )
    assert counter.driver.num_channels.source == "ca://255idc:USBCTR0:MCS:NuseAll"
    assert (
        counter.driver.current_channel.source
        == "ca://255idc:USBCTR0:MCS:CurrentChannel"
    )
    # One-shot scaler support signals
    assert counter.driver.scaler.count.source == "ca://255idc:USBCTR0:scaler1.CNT"
    assert (
        counter.driver.scaler.channels[1].description.source
        == "ca://255idc:USBCTR0:scaler1.NM2"
    )


@pytest.mark.xfail  # In development
@pytest.mark.asyncio
async def test_reading(counter):
    await counter.connect(mock=True)
    await counter.prepare(TriggerInfo())
    set_mock_value(counter.driver.clock_ticks, [2578])
    reading = await counter.read()
    # Check that the correct readings are included
    assert f"{counter.name}-elapsed_time" in reading
    assert f"{counter.name}-current_channel" in reading
    assert f"{counter.name}-clock_ticks" in reading
    assert reading[f"{counter.name}-clock_ticks"]["value"] == 2578
    assert f"{counter.name}-channels-1-raw_counts" in reading


@pytest.mark.xfail  # In development
@pytest.mark.asyncio
async def test_counter_configuration(counter):
    await counter.connect(mock=True)
    config = await counter.read_configuration()
    # Check that the correct readings are included
    assert counter.driver.mcas[0].mode.name in config
    assert counter.driver.preset_time.name in config


@pytest.mark.xfail  # In development
@pytest.mark.asyncio
async def test_scaler_reading(counter):
    await counter.connect(mock=True)
    scaler = counter.driver.scaler
    reading = await scaler.read()
    # Check that the correct readings are included
    assert scaler.elapsed_time.name in reading
    assert scaler.channels[0].net_count.name in reading


@pytest.mark.xfail  # In development
@pytest.mark.asyncio
async def test_scaler_configuration(counter):
    await counter.connect(mock=True)
    scaler = counter.driver.scaler
    config = await scaler.read_configuration()
    # Check that the correct readings are included
    assert scaler.preset_time.name in config
    assert counter.preset_time.name not in config


@pytest.mark.xfail  # In development
def test_scaler_signals(counter):
    scaler = counter.driver.scaler
    # Check individual channel signals
    assert scaler.count.source == "ca://255idcVME:3820:scaler1.CNT"
    assert scaler.count_mode.source == "ca://255idcVME:3820:scaler1.CONT"
    assert scaler.delay.source == "ca://255idcVME:3820:scaler1.DLY"
    assert scaler.auto_count_delay.source == "ca://255idcVME:3820:scaler1.DLY1"
    assert scaler.preset_time.source == "ca://255idcVME:3820:scaler1.TP"
    assert scaler.elapsed_time.source == "ca://255idcVME:3820:scaler1.T"
    assert scaler.auto_count_time.source == "ca://255idcVME:3820:scaler1.TP1"
    assert scaler.clock_frequency.source == "ca://255idcVME:3820:scaler1.FREQ"
    assert (
        scaler.record_dark_current.source
        == "ca://255idcVME:3820:scaler1_offset_start.PROC"
    )
    assert (
        scaler.dark_current_time.source == "ca://255idcVME:3820:scaler1_offset_time.VAL"
    )


@pytest.mark.xfail  # In development
def test_mca_signals(counter):
    mca = counter.driver.mcas[0]
    assert mca.spectrum.source == "ca://255idcVME:3820:mca1.VAL"
    assert mca.background.source == "ca://255idcVME:3820:mca1.BG"
    assert mca.mode.source == "ca://255idcVME:3820:mca1.MODE"


@pytest.mark.xfail  # In development
def test_scaler_channel_signals(counter):
    # Check individual channel signals
    channel = counter.driver.scaler.channels[1]
    assert channel.description.source == "ca://255idcVME:3820:scaler1.NM2"
    assert channel.is_gate.source == "ca://255idcVME:3820:scaler1.G2"
    assert channel.preset_count.source == "ca://255idcVME:3820:scaler1.PR2"
    assert channel.raw_count.source == "ca://255idcVME:3820:scaler1.S2"
    assert channel.net_count.source == "ca://255idcVME:3820:scaler1_netA.B"
    assert channel.offset_rate.source == "ca://255idcVME:3820:scaler1_offset0.B"
    # Check that dark current offsets are correct
    channel = counter.scaler.channels[15]
    assert channel.raw_count.source == "ca://255idcVME:3820:scaler1.S16"
    assert channel.net_count.source == "ca://255idcVME:3820:scaler1_netB.D"
    assert channel.offset_rate.source == "ca://255idcVME:3820:scaler1_offset3.D"
