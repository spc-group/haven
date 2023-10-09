import pytest
import time
import warnings

import numpy as np

from haven.instrument import ion_chamber
from haven import exceptions
import epics


def test_gain_level(sim_ion_chamber):
    preamp = sim_ion_chamber.preamp
    assert isinstance(preamp.sensitivity_value.get(use_monitor=False), str)
    assert isinstance(preamp.sensitivity_unit.get(use_monitor=False), str)
    # Change the preamp settings
    preamp.sensitivity_value.put("20"),
    preamp.sensitivity_unit.put("uA/V"),
    preamp.offset_value.put("2"),
    preamp.offset_unit.put("uA/V"),
    # Check that the gain level moved
    assert preamp.sensitivity_level.get(use_monitor=False) == 22
    # Move the gain level
    preamp.sensitivity_level.set(12).wait(timeout=3)
    # Check that the preamp sensitivities are moved
    assert preamp.sensitivity_value.get(use_monitor=False) == "10"
    assert preamp.sensitivity_unit.get(use_monitor=False) == "nA/V"
    # Check that the preamp sensitivity offsets are moved
    assert preamp.offset_value.get(use_monitor=False) == "1"
    assert preamp.offset_unit.get(use_monitor=False) == "nA/V"


def test_gain_changes(sim_ion_chamber):
    """Check that the gain can be turned up and down."""
    # Set some starting values
    device = sim_ion_chamber
    preamp = device.preamp
    preamp.sensitivity_value.put("5"),
    preamp.sensitivity_unit.put("nA/V"),
    assert preamp.sensitivity_value.get(use_monitor=False) == "5"
    assert preamp.sensitivity_unit.get(use_monitor=False) == "nA/V"
    # Change the gain without changing units
    preamp.sensitivity_tweak.put(1)
    assert preamp.sensitivity_value.get(use_monitor=False) == "10"
    assert preamp.sensitivity_unit.get(use_monitor=False) == "nA/V"
    preamp.sensitivity_tweak.put(-1)
    assert preamp.sensitivity_value.get(use_monitor=False) == "5"
    assert preamp.sensitivity_unit.get(use_monitor=False) == "nA/V"
    # Change the gain so that it overflows and we have to change units
    max_sensitivity = preamp.values[-1]
    max_unit = preamp.units[-1]
    preamp.sensitivity_value.put(max_sensitivity)
    assert preamp.sensitivity_value.get(use_monitor=False) == "500"
    preamp.sensitivity_tweak.set(1).wait()
    assert preamp.sensitivity_value.get(use_monitor=False) == "1"
    assert preamp.sensitivity_unit.get(use_monitor=False) == "uA/V"
    # Check that the gain can't go too low
    preamp.sensitivity_value.put("1")
    preamp.sensitivity_unit.put("pA/V")
    with warnings.catch_warnings(record=True) as ws:
        preamp.sensitivity_tweak.set(-1).wait()
        has_warning = any(["outside range" in str(w.message) for w in ws])
        assert has_warning, ws
    assert preamp.sensitivity_value.get(use_monitor=False) == "1"
    assert preamp.sensitivity_unit.get(use_monitor=False) == "pA/V"
    # Check that the gain can't go too high
    preamp.sensitivity_value.set(max_sensitivity).wait()
    preamp.sensitivity_unit.set(max_unit).wait()
    with warnings.catch_warnings(record=True) as ws:
        preamp.sensitivity_tweak.set(1).wait()
        has_warning = any(["outside range" in str(w.message) for w in ws])
        assert has_warning, ws
    assert preamp.sensitivity_value.get(use_monitor=False) == "1"
    assert preamp.sensitivity_unit.get(use_monitor=False) == "mA/V"


def test_load_ion_chambers(sim_registry):
    new_ics = ion_chamber.load_ion_chambers()
    # Test the channel info is extracted properly
    ic = sim_registry.find(label="ion_chambers")
    assert ic.ch_num == 2
    assert ic.preamp.prefix.split(":")[-1] == "SR01"


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
    flyer.clock.set(1e7)
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
