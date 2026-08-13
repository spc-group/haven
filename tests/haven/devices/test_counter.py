import time

import numpy as np
import pytest
from bluesky import RunEngine
from bluesky import plan_stubs as bps
from bluesky import preprocessors as bpp
from ophyd_async.core import TriggerInfo, set_mock_value

# Remove if bounded detector support is available in ophyd-async
try:
    from ophyd_async.core import PageableDataProvider
except ImportError:
    pytest.skip(allow_module_level=True)
else:
    del PageableDataProvider

from haven.devices.detectors.counter import Counter, CTR08Counter, SIS3820Counter


def build_counter(flavor="base"):
    classes = {
        "base": Counter,
        "sis3820": SIS3820Counter,
        "ctr08": CTR08Counter,
    }
    ThisCounter = classes[flavor]
    channels = [
        {"number": 1, "name": "I0"},
        {"number": 2, "name": "It"},
    ]
    counter = ThisCounter(
        prefix="255idc:CTR0:", channels=channels, name="jetstream_ion_chambers"
    )
    return counter


def test_signals():
    counter = build_counter()
    # Multi-channel scaler signals
    assert counter.driver.mcs.start_all.source == "ca://255idc:CTR0:MCS:StartAll"
    assert counter.driver.mcs.stop_all.source == "ca://255idc:CTR0:MCS:StopAll"
    assert counter.driver.mcs.erase_all.source == "ca://255idc:CTR0:MCS:EraseAll"
    assert counter.driver.mcs.erase_start.source == "ca://255idc:CTR0:MCS:EraseStart"
    assert counter.driver.mcs.preset_time.source == "ca://255idc:CTR0:MCS:PresetReal"
    assert counter.driver.mcs.acquiring.source == "ca://255idc:CTR0:MCS:Acquiring"
    assert counter.driver.mcs.elapsed_time.source == "ca://255idc:CTR0:MCS:ElapsedReal"
    assert (
        counter.driver.mcs.current_channel.source
        == "ca://255idc:CTR0:MCS:CurrentChannel"
    )
    assert counter.driver.mcs.prescale.source == "ca://255idc:CTR0:MCS:Prescale"
    assert (
        counter.driver.mcs.channel_advance_source.source
        == "ca://255idc:CTR0:MCS:ChannelAdvance"
    )
    assert (
        counter.driver.mcs.num_channels_max.source == "ca://255idc:CTR0:MCS:MaxChannels"
    )
    assert counter.driver.mcs.num_channels.source == "ca://255idc:CTR0:MCS:NuseAll"
    assert (
        counter.driver.mcs.current_channel.source
        == "ca://255idc:CTR0:MCS:CurrentChannel"
    )
    # One-shot scaler support signals
    assert counter.driver.scaler.count.source == "ca://255idc:CTR0:scaler1.CNT"
    assert (
        counter.driver.scaler.channels[1].description.source
        == "ca://255idc:CTR0:scaler1.NM2"
    )
    # Test that device-specific signals are not part of the generic device
    assert not hasattr(counter.driver, "model")
    assert not hasattr(counter.driver, "model_number")
    assert not hasattr(counter.driver, "unique_id")
    assert not hasattr(counter.driver, "firmware_version")
    assert not hasattr(counter.driver, "ul_version")
    assert not hasattr(counter.driver, "driver_version")
    assert not hasattr(counter.driver, "pulse_generators")


def test_signals_ctr08():
    counter = build_counter("ctr08")
    # Global device signals
    assert counter.driver.model.source == "ca://255idc:CTR0:ModelName"
    assert counter.driver.model_number.source == "ca://255idc:CTR0:ModelNumber"
    assert counter.driver.unique_id.source == "ca://255idc:CTR0:UniqueID"
    assert counter.driver.firmware_version.source == "ca://255idc:CTR0:FirmwareVersion"
    assert counter.driver.ul_version.source == "ca://255idc:CTR0:ULVersion"
    assert counter.driver.driver_version.source == "ca://255idc:CTR0:DriverVersion"
    assert (
        counter.driver.mcs.action_on_start.source == "ca://255idc:CTR0:MCS:Point0Action"
    )
    # Test this separately, CTR08 has an RBV and SIS3820 does not
    assert counter.driver.mcs.dwell_time.source == "ca://255idc:CTR0:MCS:Dwell_RBV"
    # Clocks/pulse generators
    generator = counter.driver.pulse_generators[0]
    assert generator.frequency.source == "ca://255idc:CTR0:PulseGen1Frequency_RBV"
    assert generator.period.source == "ca://255idc:CTR0:PulseGen1Period_RBV"
    assert generator.duty_cycle.source == "ca://255idc:CTR0:PulseGen1DutyCycle_RBV"
    assert generator.pulse_width.source == "ca://255idc:CTR0:PulseGen1Width_RBV"
    assert generator.running.source == "ca://255idc:CTR0:PulseGen1Run"


def test_signals_sis3820():
    counter = build_counter("sis3820")
    assert (
        counter.driver.mcs.action_on_start.source == "ca://255idc:CTR0:MCS:CountOnStart"
    )
    # Test this separately, CTR08 has an RBV and SIS3820 does not
    assert counter.driver.mcs.dwell_time.source == "ca://255idc:CTR0:MCS:Dwell"


@pytest.mark.parametrize("flavor", ["sis3820", "ctr08"])
def test_mca_signals(flavor):
    counter = build_counter(flavor)
    mca = counter.driver.mcs.mcas[1]
    assert mca.count.source == "ca://255idc:CTR0:MCS:mca2.VAL"
    assert mca.background.source == "ca://255idc:CTR0:MCS:mca2.BG"
    assert mca.mode.source == "ca://255idc:CTR0:MCS:mca2.MODE"


@pytest.mark.parametrize("flavor", ["sis3820", "ctr08"])
@pytest.mark.asyncio
async def test_reading(flavor):
    counter = build_counter(flavor)
    await counter.connect(mock=True)
    await counter.prepare(TriggerInfo())
    FREQ = 1e7
    set_mock_value(counter.driver.scaler.clock_frequency, FREQ)
    set_mock_value(counter.driver.mcs.clock.count, [2 * FREQ])
    set_mock_value(counter.driver.mcs.mcas[1].count, [1337])
    set_mock_value(counter.driver.mcs.mcas[2].count, [2448])
    now = time.time()
    reading = await counter.read()
    # Check that the correct readings are included
    assert f"{counter.name}-clock-count" in reading
    assert reading[f"{counter.name}-clock-count"]["value"] == 2 * FREQ
    assert reading[f"{counter.name}-clock-count"]["timestamp"] == pytest.approx(now)
    assert "I0-count" in reading
    assert reading["I0-count"]["value"] == 1337
    assert reading["I0-count"]["timestamp"] == pytest.approx(now)


@pytest.mark.parametrize("flavor", ["sis3820", "ctr08"])
@pytest.mark.asyncio
async def test_describe(flavor):
    counter = build_counter(flavor)
    await counter.connect(mock=True)
    await counter.prepare(TriggerInfo())
    FREQ = 1e7
    set_mock_value(counter.driver.scaler.clock_frequency, FREQ)
    set_mock_value(counter.driver.mcs.clock.count, [2 * FREQ])
    set_mock_value(counter.driver.mcs.mcas[1].count, [1337])
    set_mock_value(counter.driver.mcs.mcas[2].count, [2448])
    reading = await counter.read()
    description = await counter.describe()
    # Check that the description matches the reading
    from pprint import pprint

    pprint(reading)
    pprint(description)
    assert set(reading.keys()) == set(description.keys())


@pytest.mark.parametrize("flavor", ["sis3820", "ctr08"])
@pytest.mark.asyncio
async def test_counter_configuration(flavor):
    counter = build_counter(flavor)
    await counter.connect(mock=True)
    config = await counter.read_configuration()
    # Scaler signals
    assert counter.driver.scaler.delay.name in config
    assert counter.driver.scaler.clock_frequency.name in config
    assert counter.driver.scaler.count_mode.name in config
    assert counter.driver.scaler.preset_time.name in config
    # MCS signals
    assert counter.driver.mcs.preset_time.name in config
    assert counter.driver.mcs.prescale.name in config
    assert counter.driver.mcs.channel_advance_source.name in config
    assert counter.driver.mcs.num_channels.name in config
    assert counter.driver.mcs.num_channels_max.name in config
    assert counter.driver.mcs.clock.mode.name in config
    assert counter.driver.mcs.mcas[2].mode.name in config
    assert counter.driver.mcs.mcas[1].mode.name in config
    assert f"{counter.name}-dark_current_signals" in config
    assert config[f"{counter.name}-dark_current_signals"]["value"] == ["I0", "It"]


@pytest.mark.asyncio
async def test_usbctr08_configuration():
    """Check config signals specific to the USB-CTR08."""
    counter = build_counter("ctr08")
    await counter.connect(mock=True)
    config = await counter.read_configuration()
    assert counter.driver.model.name in config
    assert counter.driver.model_number.name in config
    assert counter.driver.unique_id.name in config
    assert counter.driver.firmware_version.name in config
    assert counter.driver.ul_version.name in config
    assert counter.driver.driver_version.name in config
    assert counter.driver.mcs.dwell_time.name in config
    assert counter.driver.mcs.action_on_start.name in config
    assert counter.driver.pulse_generators[0].frequency.name in config
    assert counter.driver.pulse_generators[0].period.name in config
    assert counter.driver.pulse_generators[0].frequency.name in config
    assert counter.driver.pulse_generators[0].duty_cycle.name in config
    assert counter.driver.pulse_generators[0].pulse_width.name in config
    assert counter.driver.pulse_generators[0].running.name in config


@pytest.mark.asyncio
async def test_sis3820_configuration():
    """Check config signals specific to the Struck SIS3820."""
    counter = build_counter("sis3820")
    await counter.connect(mock=True)
    config = await counter.read_configuration()
    assert counter.driver.mcs.dwell_time.name in config
    assert counter.driver.mcs.action_on_start.name in config
    assert counter.driver.mcs.clock_source.name in config
    assert counter.driver.mcs.acquire_mode.name in config
    assert counter.driver.mcs.input_mode.name in config
    assert counter.driver.mcs.input_polarity.name in config


@pytest.mark.parametrize("flavor", ["sis3820", "ctr08"])
def test_scaler_signals(flavor):
    counter = build_counter(flavor)
    scaler = counter.driver.scaler
    # Check individual channel signals
    assert scaler.count.source == "ca://255idc:CTR0:scaler1.CNT"
    assert scaler.count_mode.source == "ca://255idc:CTR0:scaler1.CONT"
    assert scaler.delay.source == "ca://255idc:CTR0:scaler1.DLY"
    assert scaler.auto_count_delay.source == "ca://255idc:CTR0:scaler1.DLY1"
    assert scaler.preset_time.source == "ca://255idc:CTR0:scaler1.TP"
    assert scaler.elapsed_time.source == "ca://255idc:CTR0:scaler1.T"
    assert scaler.auto_count_time.source == "ca://255idc:CTR0:scaler1.TP1"
    assert scaler.clock_frequency.source == "ca://255idc:CTR0:scaler1.FREQ"
    # Check individual channel signals
    channel = scaler.channels[1]
    assert channel.description.source == "ca://255idc:CTR0:scaler1.NM2"
    assert channel.is_gate.source == "ca://255idc:CTR0:scaler1.G2"
    assert channel.preset_count.source == "ca://255idc:CTR0:scaler1.PR2"
    assert channel.raw_count.source == "ca://255idc:CTR0:scaler1.S2"


@pytest.mark.parametrize("flavor", ["sis3820", "ctr08"])
async def test_collection(flavor):
    counter = build_counter(flavor)
    await counter.connect(mock=True)
    # Run this in the run engine to make sure we don't collect stream assets
    RE = RunEngine({}, call_returns_result=True)

    docs = {}

    def stash_docs(name, doc):
        docs.setdefault(name, []).append(doc)

    RE.subscribe(stash_docs)

    @bpp.stage_decorator([counter])
    @bpp.run_decorator()
    def dummy_fly_scan():
        yield from bps.prepare(counter, TriggerInfo(), wait=True)
        yield from bps.declare_stream(counter, name="the_stream")
        yield from bps.kickoff(counter, wait=False, group="kickoff_group")
        set_mock_value(counter.driver.mcs.acquiring, True)
        yield from bps.wait("kickoff_group")
        yield from bps.complete(counter, wait=False, group="complete_group")
        set_mock_value(counter.driver.mcs.current_channel, 1)
        set_mock_value(counter.driver.mcs.acquiring, False)
        # Set fake data
        FREQ = 1e7
        set_mock_value(counter.driver.scaler.clock_frequency, FREQ)
        set_mock_value(counter.driver.mcs.clock.count, [2 * FREQ, 2.1 * FREQ])
        set_mock_value(counter.driver.mcs.mcas[1].count, [1337, 1447])
        set_mock_value(counter.driver.mcs.mcas[2].count, [2448, 2558])
        yield from bps.wait("complete_group")
        yield from bps.collect(counter)

    RE(dummy_fly_scan())
    assert "event_page" in docs.keys()
    data = docs["event_page"][0]["data"]
    timestamps = docs["event_page"][0]["timestamps"]
    now = time.time()
    assert list(data["I0-count"]) == [1337, 1447]
    assert list(data["It-count"]) == [2448, 2558]
    assert list(data["jetstream_ion_chambers-clock-count"]) == [2e7, 2.1e7]
    np.testing.assert_allclose(timestamps["I0-count"], [now - 2.1, now])


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2026, UChicago Argonne, LLC
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
