import time
from unittest import mock

import numpy as np
import pytest

from haven.instrument import ion_chamber


@pytest.fixture()
def preamp(sim_ion_chamber):
    preamp = sim_ion_chamber.preamp
    return preamp


def test_get_gain_level(preamp):
    # Change the preamp settings
    preamp.sensitivity_value.put("20")
    assert preamp.sensitivity_value.get(as_string=True) == "20"
    assert preamp.sensitivity_value.get(as_string=False) == 4
    preamp.sensitivity_unit.put("uA/V"),
    preamp.offset_value.put(1),  # 2 uA/V
    preamp.offset_unit.put(2),
    # Check that the gain level moved
    assert preamp.sensitivity_level.get(use_monitor=False) == 22


def test_put_gain_level(preamp):
    # Move the gain level
    preamp.sensitivity_level.set(12).wait(timeout=3)
    # Check that the preamp sensitivities are moved
    assert preamp.sensitivity_value.get(use_monitor=False) == "10"
    assert preamp.sensitivity_unit.get(use_monitor=False) == "nA/V"
    # Check that the preamp sensitivity offsets are moved
    assert preamp.offset_value.get(use_monitor=False) == "1"
    assert preamp.offset_unit.get(use_monitor=False) == "nA"


def test_gain_level_settling(preamp, monkeypatch):
    # Make it really low to start
    preamp.sensitivity_level.set(27).wait(timeout=3)
    preamp.gain_mode.set("LOW NOISE").wait(timeout=3)
    # Set up patches to watch the real signals getting set
    monkeypatch.setattr(preamp.sensitivity_value, 'set', mock.MagicMock())
    monkeypatch.setattr(preamp.sensitivity_unit, 'set', mock.MagicMock()) 
    # Now make the gain high so we can check the settle time
    preamp.sensitivity_level.set(0)
    # Check that the right settle time was used
    preamp.sensitivity_value.set.assert_called_with(0, timeout=None, settle_time=2)
    preamp.sensitivity_unit.set.assert_called_with("pA/V", timeout=None, settle_time=2)
    


def test_gain_signals(preamp):
    # Change the preamp settings
    preamp.sensitivity_value.put("20")
    preamp.sensitivity_unit.put("uA/V")
    preamp.offset_value.put("2")
    preamp.offset_unit.put("uA")
    # Check the gain and gain_db signals
    assert preamp.gain.get(use_monitor=False) == pytest.approx(1 / 20e-6)
    assert preamp.gain_db.get(use_monitor=False) == pytest.approx(46.9897)


def test_load_ion_chambers(sim_registry):
    new_ics = ion_chamber.load_ion_chambers()
    # Test the channel info is extracted properly
    ic = sim_registry.find(label="ion_chambers")
    assert ic.ch_num == 2
    assert ic.preamp.prefix.strip(":").split(":")[-1] == "SR02"
    assert ic.voltmeter.prefix == "255idc:LabjackT7_0:Ai0"


def test_default_pv_prefix():
    """Check that it uses the *prefix* argument if no *scaler_prefix* is
    given.

    """
    prefix = "myioc:myscaler"
    # Instantiate the device with *scaler_prefix* argument
    device = ion_chamber.IonChamber(
        name="device", prefix="gibberish", ch_num=1, scaler_prefix=prefix
    )
    device.scaler_prefix = prefix
    assert device.scaler_prefix == prefix
    # Instantiate the device with *scaler_prefix* argument
    device = ion_chamber.IonChamber(name="device", ch_num=1, prefix=prefix)
    assert device.scaler_prefix == prefix


def test_volts_signal(sim_ion_chamber):
    """Test that the scaler tick counts get properly converted to pre-amp voltage."""
    chamber = sim_ion_chamber
    # Set the necessary dependent signals
    chamber.counts.sim_put(int(0.13e7))  # 1.3 V
    chamber.clock_ticks.sim_put(1e7)  # 10 MHz clock
    # Check the volts answer
    assert chamber.volts.get() == 1.30


def test_amps_signal(sim_ion_chamber):
    """Test that the scaler tick counts get properly converted to ion chamber current."""
    chamber = sim_ion_chamber
    # Set the necessary dependent signals
    chamber.counts.sim_put(int(0.13e7))  # 1.3V
    chamber.clock_ticks.sim_put(1e7)  # 10 MHz clock
    chamber.preamp.gain.put(1 / 2e-5)  # 20 µA/V to V/A
    # Make sure it ignores the offset if it's off
    chamber.preamp.offset_on.put("OFF")
    chamber.preamp.offset_value.put("2")  # 2
    chamber.preamp.offset_unit.put("uA")  # µA
    # Check the current answer
    assert chamber.amps.get() == pytest.approx(2.6e-5)


def test_amps_signal_with_offset(sim_ion_chamber):
    """Test that the scaler tick counts get properly converted to pre-amp voltage."""
    chamber = sim_ion_chamber
    # Set the necessary dependent signals
    chamber.counts.sim_put(int(0.13e7))  # 1.3V
    chamber.clock_ticks.sim_put(1e7)  # 10 MHz clock
    chamber.preamp.gain.put(1 / 2e-5)  # 20 µA/V to V/A
    chamber.preamp.offset_on.put("ON")
    chamber.preamp.offset_sign.put("-")
    chamber.preamp.offset_value.put("2")  # 2
    chamber.preamp.offset_unit.put("uA")  # µA
    # Check the current answer
    assert chamber.amps.get() == pytest.approx(2.8e-5)


def test_voltmeter_amps_signal(sim_ion_chamber):
    """Test that the voltmeter voltage gets properly converted to ion
    chamber current.

    """
    chamber = sim_ion_chamber
    # Set the necessary dependent signals
    chamber.voltmeter.volts.sim_put(1.3)  # 1.3V
    chamber.preamp.gain.put(1 / 2e-5)  # 20 µA/V to V/A
    # Make sure it ignores the offset if it's off
    chamber.preamp.offset_on.put("OFF")
    chamber.preamp.offset_value.put("2")  # 2
    chamber.preamp.offset_unit.put("uA")  # µA
    # Check the current answer
    assert chamber.voltmeter.amps.get() == pytest.approx(2.6e-5)


def test_voltmeter_name(sim_ion_chamber):
    chamber = sim_ion_chamber
    assert chamber.voltmeter.description.get() != "Icake"
    # Change the ion chamber name, and see if the voltmeter name updates
    chamber.description.put("Icake")
    assert chamber.voltmeter.description.get() == "Icake"


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
        (2, "offset0.B"),
        (3, "offset0.C"),
        (4, "offset0.D"),
        (5, "offset1.A"),
        (6, "offset1.B"),
        (7, "offset1.C"),
        (8, "offset1.D"),
        (9, "offset2.A"),
        (10, "offset2.B"),
        (11, "offset2.C"),
        (12, "offset2.D"),
    ]
    for ch_num, suffix in channel_suffixes:
        ic = ion_chamber.IonChamber(
            prefix="scaler_ioc", ch_num=ch_num, name=f"ion_chamber_{ch_num}"
        )
        assert ic.offset.pvname == f"scaler_ioc:scaler1_{suffix}", f"channel {ch_num}"


def test_flyscan_kickoff(sim_ion_chamber):
    flyer = sim_ion_chamber
    flyer.num_bins.set(10)
    status = flyer.kickoff()
    flyer.acquiring.set(1)
    status.wait()
    assert status.success
    assert status.done
    # Check that the device was properly configured for fly-scanning
    assert flyer.erase_start._readback == 1
    assert flyer.timestamps == []
    # Check that timestamps get recorded when new data are available
    flyer.current_channel.set(1).wait()
    assert flyer.timestamps[0] == pytest.approx(time.time())


def test_flyscan_complete(sim_ion_chamber):
    flyer = sim_ion_chamber
    # Run the complete method
    status = flyer.complete()
    status.wait()
    # Check that the detector is stopped
    assert flyer.stop_all._readback == 1


def test_flyscan_collect(sim_ion_chamber):
    flyer = sim_ion_chamber
    name = flyer.net_counts.name
    flyer.start_timestamp = 988.0
    # Make fake fly-scan data
    sim_data = np.zeros(shape=(8000,))
    sim_data[:6] = [3, 5, 8, 13, 2, 33]
    flyer.mca.spectrum._readback = sim_data
    sim_times = np.asarray([12.0e7, 4.0e7, 4.0e7, 4.0e7, 4.0e7, 4.0e7])
    flyer.mca_times.spectrum._readback = sim_times
    flyer.frequency.set(1e7).wait()
    # Ignore the first collected data point because it's during taxiing
    expected_data = sim_data[1:]
    # The real timestamps should be midway between PSO pulses
    flyer.timestamps = [1000, 1004, 1008, 1012, 1016, 1020]
    expected_timestamps = [1002.0, 1006.0, 1010.0, 1014.0, 1018.0]
    payload = list(flyer.collect())
    # Confirm data have the right structure
    for datum, value, timestamp in zip(payload, expected_data, expected_timestamps):
        assert datum == {
            "data": {name: [value]},
            "timestamps": {name: [timestamp]},
            "time": timestamp,
        }


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
