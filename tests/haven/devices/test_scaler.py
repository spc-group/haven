import pytest

from haven.devices.scaler import MultiChannelScaler


@pytest.fixture()
def mcs(sim_registry):
    mcs = MultiChannelScaler("255idcVME:3820:", channels=range(16), name="sis3820")
    return mcs


def test_mcs_signals(mcs):
    # Multi-channel scaler signals
    assert mcs.start_all.source == "ca://255idcVME:3820:StartAll"
    assert mcs.stop_all.source == "ca://255idcVME:3820:StopAll"
    assert mcs.erase_all.source == "ca://255idcVME:3820:EraseAll"
    assert mcs.erase_start.source == "ca://255idcVME:3820:EraseStart"
    assert mcs.preset_time.source == "ca://255idcVME:3820:PresetReal"
    assert mcs.acquiring.source == "ca://255idcVME:3820:Acquiring"
    assert mcs.elapsed_time.source == "ca://255idcVME:3820:ElapsedReal"
    assert mcs.current_channel.source == "ca://255idcVME:3820:CurrentChannel"
    assert mcs.dwell_time.source == "ca://255idcVME:3820:Dwell"
    assert mcs.prescale.source == "ca://255idcVME:3820:Prescale"
    assert mcs.channel_advance_source.source == "ca://255idcVME:3820:ChannelAdvance"
    assert mcs.count_on_start.source == "ca://255idcVME:3820:CountOnStart"
    assert (
        mcs.software_channel_advance.source
        == "ca://255idcVME:3820:SoftwareChannelAdvance"
    )
    assert mcs.channel_1_source.source == "ca://255idcVME:3820:Channel1Source"
    assert mcs.user_led.source == "ca://255idcVME:3820:UserLED"
    assert mcs.mux_output.source == "ca://255idcVME:3820:MUXOutput"
    assert mcs.acquire_mode.source == "ca://255idcVME:3820:AcquireMode"
    assert mcs.input_mode.source == "ca://255idcVME:3820:InputMode"
    assert mcs.input_polarity.source == "ca://255idcVME:3820:InputPolarity"
    assert mcs.output_mode.source == "ca://255idcVME:3820:OutputMode"
    assert mcs.output_polarity.source == "ca://255idcVME:3820:OutputPolarity"
    assert mcs.lne_output_stretcher.source == "ca://255idcVME:3820:LNEStretcherEnable"
    assert mcs.lne_output_polarity.source == "ca://255idcVME:3820:LNEOutputPolarity"
    assert mcs.lne_output_delay.source == "ca://255idcVME:3820:LNEOutputDelay"
    assert mcs.lne_output_width.source == "ca://255idcVME:3820:LNEOutputWidth"
    assert mcs.num_channels_max.source == "ca://255idcVME:3820:MaxChannels"
    assert mcs.num_channels.source == "ca://255idcVME:3820:NuseAll"
    assert mcs.current_channel.source == "ca://255idcVME:3820:CurrentChannel"
    assert mcs.snl_connected.source == "ca://255idcVME:3820:SNL_Connected"
    assert mcs.model.source == "ca://255idcVME:3820:Model"
    assert mcs.firmware.source == "ca://255idcVME:3820:Firmware"


@pytest.mark.asyncio
async def test_mcs_reading(mcs):
    await mcs.connect(mock=True)
    reading = await mcs.read()
    # Check that the correct readings are included
    assert mcs.elapsed_time.name in reading
    assert mcs.current_channel.name in reading
    assert mcs.mcas[0].spectrum.name in reading
    # The scaler is also read by the MCS by default
    assert mcs.scaler.elapsed_time.name in reading


@pytest.mark.asyncio
async def test_mcs_configuration(mcs):
    await mcs.connect(mock=True)
    config = await mcs.read_configuration()
    # Check that the correct readings are included
    assert mcs.mcas[0].mode.name in config
    assert mcs.preset_time.name in config


@pytest.mark.asyncio
async def test_scaler_reading(mcs):
    await mcs.connect(mock=True)
    scaler = mcs.scaler
    reading = await scaler.read()
    # Check that the correct readings are included
    assert scaler.elapsed_time.name in reading
    assert scaler.channels[0].net_count.name in reading


@pytest.mark.asyncio
async def test_scaler_configuration(mcs):
    await mcs.connect(mock=True)
    scaler = mcs.scaler
    config = await scaler.read_configuration()
    # Check that the correct readings are included
    assert scaler.preset_time.name in config
    assert mcs.preset_time.name not in config


def test_scaler_signals(mcs):
    scaler = mcs.scaler
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


def test_mca_signals(mcs):
    mca = mcs.mcas[0]
    assert mca.spectrum.source == "ca://255idcVME:3820:mca1.VAL"
    assert mca.background.source == "ca://255idcVME:3820:mca1.BG"
    assert mca.mode.source == "ca://255idcVME:3820:mca1.MODE"


def test_scaler_channel_signals(mcs):
    # Check individual channel signals
    channel = mcs.scaler.channels[1]
    assert channel.description.source == "ca://255idcVME:3820:scaler1.NM2"
    assert channel.is_gate.source == "ca://255idcVME:3820:scaler1.G2"
    assert channel.preset_count.source == "ca://255idcVME:3820:scaler1.PR2"
    assert channel.raw_count.source == "ca://255idcVME:3820:scaler1.S2"
    assert channel.net_count.source == "ca://255idcVME:3820:scaler1_netA.B"
    assert channel.offset_rate.source == "ca://255idcVME:3820:scaler1_offset0.B"
    # Check that dark current offsets are correct
    channel = mcs.scaler.channels[15]
    assert channel.raw_count.source == "ca://255idcVME:3820:scaler1.S16"
    assert channel.net_count.source == "ca://255idcVME:3820:scaler1_netB.D"
    assert channel.offset_rate.source == "ca://255idcVME:3820:scaler1_offset3.D"
