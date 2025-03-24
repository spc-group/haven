import asyncio
from unittest.mock import AsyncMock

import numpy as np
import pytest
from numpy.testing import assert_allclose
from ophyd_async.core import TriggerInfo
from ophyd_async.testing import assert_value, get_mock_put, set_mock_value

from haven.devices.ion_chamber import IonChamber


@pytest.fixture()
def preamp(sim_ion_chamber):
    preamp = sim_ion_chamber.preamp
    return preamp


@pytest.fixture()
def ion_chamber(sim_registry):
    ion_chamber = IonChamber(
        scaler_prefix="255idcVME:3820:",
        scaler_channel=2,
        preamp_prefix="255idc:SR03:",
        voltmeter_prefix="255idc:LabjackT7_1:",
        voltmeter_channel=1,
        counts_per_volt_second=1e6,
        name="I0",
    )
    return ion_chamber


def test_ion_chamber_devices(ion_chamber):
    """Check that the ion chamber has the right sub-devices."""
    assert list(ion_chamber.mcs.scaler.channels.keys()) == [0, 2]
    assert hasattr(ion_chamber, "preamp")
    assert list(ion_chamber.voltmeter.analog_inputs.keys()) == [1]


async def test_readables(ion_chamber):
    await ion_chamber.connect(mock=True)
    expected_readables = [
        "I0-net_current",
        "I0-raw_current",
        "I0-voltmeter-analog_inputs-1-final_value",
        "I0-mcs-scaler-channels-0-net_count",
        "I0-mcs-scaler-channels-0-raw_count",
        "I0-mcs-scaler-channels-2-net_count",
        "I0-mcs-scaler-channels-2-raw_count",
        "I0-mcs-scaler-elapsed_time",
    ]
    actual_readables = (await ion_chamber.describe()).keys()
    assert sorted(actual_readables) == sorted(expected_readables)
    # Check signal hints
    expected_hints = [
        "I0-net_current",
    ]
    actual_hints = ion_chamber.hints["fields"]
    assert sorted(actual_hints) == sorted(expected_hints)
    # Check configurables
    expected_configables = [
        "I0-counts_per_volt_second",
        "I0-voltmeter-model_name",
        "I0-voltmeter-poll_sleep_ms",
        "I0-voltmeter-analog_in_sampling_rate",
        "I0-voltmeter-last_error_message",
        "I0-voltmeter-analog_in_resolution_all",
        "I0-voltmeter-firmware_version",
        "I0-voltmeter-device_temperature",
        "I0-voltmeter-serial_number",
        "I0-voltmeter-analog_in_settling_time_all",
        "I0-voltmeter-driver_version",
        "I0-voltmeter-ljm_version",
        "I0-voltmeter-analog_inputs-1-mode",
        "I0-voltmeter-analog_inputs-1-temperature_units",
        "I0-voltmeter-analog_inputs-1-low",
        "I0-voltmeter-analog_inputs-1-high",
        "I0-voltmeter-analog_inputs-1-resolution",
        "I0-voltmeter-analog_inputs-1-range",
        "I0-voltmeter-analog_inputs-1-differential",
        "I0-voltmeter-analog_inputs-1-enable",
        "I0-voltmeter-analog_inputs-1-input_link",
        "I0-voltmeter-analog_inputs-1-description",
        "I0-voltmeter-analog_inputs-1-scanning_rate",
        "I0-voltmeter-analog_inputs-1-device_type",
        "I0-mcs-model",
        "I0-mcs-lne_output_delay",
        "I0-mcs-count_on_start",
        "I0-mcs-lne_output_polarity",
        "I0-mcs-lne_output_stretcher",
        "I0-mcs-preset_time",
        "I0-mcs-channel_1_source",
        "I0-mcs-firmware",
        "I0-mcs-input_mode",
        "I0-mcs-output_mode",
        "I0-mcs-channel_advance_source",
        "I0-mcs-snl_connected",
        "I0-mcs-prescale",
        "I0-mcs-output_polarity",
        "I0-mcs-num_channels",
        "I0-mcs-input_polarity",
        "I0-mcs-lne_output_width",
        "I0-mcs-mux_output",
        "I0-mcs-acquire_mode",
        "I0-mcs-num_channels_max",
        "I0-mcs-dwell_time",
        "I0-mcs-scaler-channels-0-preset_count",
        "I0-mcs-scaler-channels-0-description",
        "I0-mcs-scaler-channels-0-is_gate",
        "I0-mcs-scaler-channels-0-offset_rate",
        "I0-mcs-scaler-channels-2-preset_count",
        "I0-mcs-scaler-channels-2-description",
        "I0-mcs-scaler-channels-2-is_gate",
        "I0-mcs-scaler-channels-2-offset_rate",
        "I0-mcs-scaler-delay",
        "I0-mcs-scaler-clock_frequency",
        "I0-mcs-scaler-preset_time",
        "I0-mcs-scaler-count_mode",
    ]
    actual_configables = (await ion_chamber.describe_configuration()).keys()
    assert sorted(actual_configables) == sorted(expected_configables)


@pytest.mark.asyncio
async def test_trigger(ion_chamber):
    await ion_chamber.connect(mock=True)
    set_mock_value(ion_chamber.mcs.scaler.clock_frequency, 50e6)
    assert ion_chamber._trigger_statuses == {}
    # Does the same trigger twice return the same
    status1 = ion_chamber.trigger()
    status2 = ion_chamber.trigger()
    assert not status1.done
    assert not status2.done
    await status1
    assert status1.done
    await status2
    assert status2.done


@pytest.mark.asyncio
async def test_trigger_dark_current(ion_chamber, monkeypatch):
    await ion_chamber.connect(mock=True)
    monkeypatch.setattr(
        ion_chamber.mcs.scaler.record_dark_current, "trigger", AsyncMock()
    )
    status = ion_chamber.trigger(record_dark_current=True)
    await status
    assert ion_chamber.mcs.scaler.record_dark_current.trigger.called


async def test_default_timeout_with_time(ion_chamber):
    await ion_chamber.connect(mock=True)
    await ion_chamber.mcs.scaler.channels[0].is_gate.set(True)
    await ion_chamber.mcs.scaler.preset_time.set(17)
    timeout = await ion_chamber.default_timeout()
    assert timeout == pytest.approx(27)


async def test_default_timeout_with_gate(ion_chamber):
    """If another channel is gated, then use the maximum timeout.

    Assume the internal register is 32-bit, then we can count for at most:

      2**32 / clock_freq

    """
    clock_freq = 50e6
    await ion_chamber.connect(mock=True)
    await ion_chamber.mcs.scaler.channels[0].is_gate.set(False)
    await ion_chamber.mcs.scaler.clock_frequency.set(clock_freq)
    timeout = await ion_chamber.default_timeout()
    buff_size = 2**32
    assert timeout == pytest.approx(buff_size / clock_freq + 10)


@pytest.mark.asyncio
async def test_net_current_signal(ion_chamber):
    """Test that scaler tick counts get properly converted to ion chamber current."""
    await ion_chamber.connect(mock=True)
    await asyncio.gather(
        ion_chamber.net_current.connect(mock=False),
        ion_chamber.preamp.gain.connect(mock=False),
    )
    # Set the necessary dependent signals
    set_mock_value(ion_chamber.counts_per_volt_second, 10e6)  # 100 Mhz / 10 V
    set_mock_value(ion_chamber.scaler_channel.net_count, int(13e6))  # 1.3V
    set_mock_value(ion_chamber.mcs.scaler.clock_frequency, 9.6e6)
    set_mock_value(ion_chamber.mcs.scaler.channels[0].raw_count, 4.8e6)
    set_mock_value(ion_chamber.preamp.sensitivity_value, "20")
    set_mock_value(ion_chamber.preamp.sensitivity_unit, "uA/V")
    # Make sure it ignores the offset if it's off
    set_mock_value(ion_chamber.preamp.offset_on, "OFF")
    set_mock_value(ion_chamber.preamp.offset_value, "2")
    set_mock_value(ion_chamber.preamp.offset_unit, "uA")
    # Check the current answer
    assert (await ion_chamber.net_current.get_value()) == pytest.approx(5.2e-5)


@pytest.mark.asyncio
async def test_raw_current_signal(ion_chamber):
    """Test that scaler tick counts get properly converted to ion chamber current."""
    await ion_chamber.connect(mock=True)
    await asyncio.gather(
        ion_chamber.raw_current.connect(mock=False),
        ion_chamber.preamp.gain.connect(mock=False),
    )
    # Set the necessary dependent signals
    set_mock_value(ion_chamber.counts_per_volt_second, 10e6)  # 100 Mhz / 10 V
    set_mock_value(ion_chamber.scaler_channel.raw_count, int(13e6))  # 1.3V
    set_mock_value(ion_chamber.mcs.scaler.clock_frequency, 9.6e6)
    set_mock_value(ion_chamber.mcs.scaler.channels[0].raw_count, 4.8e6)
    set_mock_value(ion_chamber.preamp.sensitivity_value, "20")
    set_mock_value(ion_chamber.preamp.sensitivity_unit, "uA/V")
    # Make sure it ignores the offset if it's off
    set_mock_value(ion_chamber.preamp.offset_on, "OFF")
    set_mock_value(ion_chamber.preamp.offset_value, "2")
    set_mock_value(ion_chamber.preamp.offset_unit, "uA")
    # Check the current answer
    assert (await ion_chamber.raw_current.get_value()) == pytest.approx(5.2e-5)


async def test_voltmeter_name(ion_chamber):
    ion_chamber.auto_name = True
    await ion_chamber.connect(mock=True)
    assert (await ion_chamber.voltmeter_channel.description.get_value()) != "Icake"
    # Change the ion chamber name, and see if the voltmeter name updates
    # set_mock_value(ion_chamber.scaler_channel.description, "Icake")
    ion_chamber.scaler_channel.description.get_value = AsyncMock(return_value="Icake")
    assert (await ion_chamber.scaler_channel.description.get_value()) == "Icake"
    await ion_chamber.connect(mock=True)
    assert (await ion_chamber.scaler_channel.description.get_value()) == "Icake"
    assert (await ion_chamber.voltmeter_channel.description.get_value()) == "Icake"


def test_offset_pv(sim_registry):
    """Check that the device handles the weird offset numbering scheme.

    Net count PVs in the scaler go as

    - 25idcVME:3820:scaler1_netA.B
    - 25idcVME:3820:scaler1_netA.C
    - etc.

    but the offset PVs go
    - 25idcVME:3820:scaler1_offset0.B
    - ...
    - 25idcVME:3820:scaler1_offset0.D
    - 25idcVME:3820:scaler1_offset1.A
    - ...

    """
    channel_suffixes = [
        (1, "offset0.B"),
        (2, "offset0.C"),
        (3, "offset0.D"),
        (4, "offset1.A"),
        (5, "offset1.B"),
        (6, "offset1.C"),
        (7, "offset1.D"),
        (8, "offset2.A"),
        (9, "offset2.B"),
        (10, "offset2.C"),
        (11, "offset2.D"),
    ]
    for ch_num, suffix in channel_suffixes:
        ic = IonChamber(
            scaler_prefix="scaler_ioc:",
            scaler_channel=ch_num,
            preamp_prefix="",
            voltmeter_prefix="",
            voltmeter_channel=2,
            counts_per_volt_second=1,
            name=f"ion_chamber_{ch_num}",
        )
        assert (
            ic.scaler_channel.offset_rate.source == f"ca://scaler_ioc:scaler1_{suffix}"
        ), f"channel {ch_num}"


@pytest.fixture()
def trigger_info():
    return TriggerInfo(
        number_of_triggers=5, trigger="internal", deadtime=0, livetime=1.3
    )


async def test_flyscan_prepare(ion_chamber, trigger_info):
    # Prepare the ion chamber with mocked put commands
    await ion_chamber.connect(mock=True)
    set_mock_value(ion_chamber.mcs.num_channels_max, 8000)
    erase_mock_put = get_mock_put(ion_chamber.mcs.erase_all)
    assert not erase_mock_put.called
    # Prepare the ion chamber
    await ion_chamber.prepare(trigger_info)
    # Check that the device was properly configured for fly-scanning
    assert erase_mock_put.called
    await assert_value(ion_chamber.mcs.channel_advance_source, "Internal")
    await assert_value(ion_chamber.mcs.num_channels, 8000)
    await assert_value(ion_chamber.mcs.dwell_time, 1.3)
    assert ion_chamber._fly_readings == []


async def test_flyscan_kickoff(ion_chamber, trigger_info):
    await ion_chamber.connect(mock=True)
    await ion_chamber.prepare(trigger_info)
    # Prepare the mocked put commands
    start_mock_put = get_mock_put(ion_chamber.mcs.start_all)
    # Kickoff the fly scan
    status = ion_chamber.kickoff()
    set_mock_value(ion_chamber.mcs.acquiring, ion_chamber.mcs.Acquiring.ACQUIRING)
    await status
    # Check that the scan was started
    assert start_mock_put.called
    # Check that timestamps get recorded when new data are available
    set_mock_value(ion_chamber.mcs.current_channel, 0)
    assert len(ion_chamber._fly_readings) == 1


async def test_flyscan_complete(ion_chamber):
    await ion_chamber.connect(mock=True)
    # Run the complete method
    await ion_chamber.complete()
    # Check that the detector is stopped
    assert get_mock_put(ion_chamber.mcs.stop_all).called


async def test_flyscan_collect(ion_chamber, trigger_info):
    await ion_chamber.connect(mock=True)
    # Make fake fly-scan data
    sim_data = np.zeros(shape=(8000,))
    sim_data[:6] = [3, 5, 8, 13, 2, 33]
    sim_raw_data = np.zeros_like(sim_data)
    sim_raw_data[:6] = sim_data[:6] + 12
    set_mock_value(ion_chamber.mcs.mcas[2].spectrum, sim_raw_data)
    set_mock_value(ion_chamber.scaler_channel.offset_rate, 3)
    sim_times = np.asarray([4.0e7, 4.0e7, 4.0e7, 4.0e7, 4.0e7, 4.0e7])
    set_mock_value(ion_chamber.mcs.mcas[0].spectrum, sim_times)
    set_mock_value(ion_chamber.mcs.scaler.clock_frequency, 1e7)
    channel_numbers = range(len(sim_times) + 1)
    expected_timestamps = [1004, 1008, 1012, 1016, 1020, 1024]
    ion_chamber._fly_readings = [
        {
            ion_chamber.mcs.current_channel.name: {
                "value": datum,
                "timestamp": timestamp,
                "alarm_severity": 0,
            }
        }
        for (datum, timestamp) in zip(channel_numbers, expected_timestamps)
    ]
    # The real timestamps should be midway between PSO pulses
    collected = [c async for c in ion_chamber.collect_pages()]
    assert len(collected) == 1
    collected = collected[0]
    # Confirm data have the right structure
    assert collected["time"] == 1024
    assert_allclose(
        collected["data"][ion_chamber.scaler_channel.raw_count.name], sim_raw_data[:6]
    )
    assert_allclose(
        collected["data"][ion_chamber.scaler_channel.net_count.name], sim_data[:6]
    )
    assert_allclose(
        collected["data"][ion_chamber.mcs.scaler.elapsed_time.name], [4] * 6
    )
    assert_allclose(
        collected["timestamps"][ion_chamber.scaler_channel.raw_count.name],
        expected_timestamps,
    )
    assert_allclose(
        collected["timestamps"][ion_chamber.scaler_channel.net_count.name],
        expected_timestamps,
    )
    assert_allclose(
        collected["timestamps"][ion_chamber.mcs.scaler.elapsed_time.name],
        expected_timestamps,
    )


def test_default_time_signal(ion_chamber):
    assert ion_chamber.default_time_signal.source == "ca://255idcVME:3820:scaler1.TP"


@pytest.mark.asyncio
async def test_auto_naming_default(ion_chamber, monkeypatch):
    monkeypatch.setattr(
        ion_chamber.mcs.scaler.channels[2].description,
        "get_value",
        AsyncMock(return_value="I0"),
    )
    ion_chamber.auto_name = None
    ion_chamber.set_name("")
    await ion_chamber.connect(mock=True)
    assert ion_chamber.name == "I0"
    assert ion_chamber.mcs.name == "I0-mcs"


@pytest.mark.asyncio
async def test_auto_naming(ion_chamber, monkeypatch):
    monkeypatch.setattr(
        ion_chamber.mcs.scaler.channels[2].description,
        "get_value",
        AsyncMock(return_value="I0"),
    )
    ion_chamber.auto_name = True
    ion_chamber.set_name("")
    await ion_chamber.connect(mock=True)
    assert ion_chamber.name == "I0"
    assert ion_chamber.mcs.name == "I0-mcs"


@pytest.mark.asyncio
async def test_manual_naming(ion_chamber, monkeypatch):
    ion_chamber.set_name("")
    ion_chamber.auto_name = False
    await ion_chamber.connect(mock=True)
    assert ion_chamber.name == ""
    assert ion_chamber.mcs.name == ""


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
