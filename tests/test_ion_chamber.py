import pytest
import time

from haven.instrument.ion_chamber import IonChamber, SensitivityLevelPositioner
from haven import exceptions
import epics


def test_gain_level(ioc_preamp, ioc_scaler):
    positioner = SensitivityLevelPositioner("preamp_ioc", name="positioner")
    positioner.wait_for_connection()
    assert positioner.get(use_monitor=False).sens_value.readback == epics.caget(
        "preamp_ioc:sens_num.VAL"
    )
    assert positioner.get(use_monitor=False).sens_unit.readback == epics.caget(
        "preamp_ioc:sens_unit.VAL"
    )
    # Move the gain level
    positioner.sens_level.set(12)
    time.sleep(0.1)  # Caproto breaks pseudopositioner status
    # Check that the preamp sensitivities are moved
    assert positioner.get(use_monitor=False).sens_value.readback == 3
    assert positioner.get(use_monitor=False).sens_unit.readback == 1
    # Change the preamp settings
    epics.caput("preamp_ioc:sens_num.VAL", 0)
    epics.caput("preamp_ioc:sens_unit.VAL", 3)
    time.sleep(0.1)
    # Check that the gain level moved
    assert positioner.sens_level.get(use_monitor=False).readback == 27


def test_gain_changes(ioc_preamp, ioc_scaler):
    # Setup the ion chamber and connect to the IOC
    ion_chamber = IonChamber(
        prefix="vme_crate_ioc", preamp_prefix="preamp_ioc", ch_num=2, name="ion_chamber"
    )
    time.sleep(0.01)
    ion_chamber.wait_for_connection(timeout=20)
    statuses = [ion_chamber.sensitivity.sens_value.set(2),
                ion_chamber.sensitivity.sens_unit.set(1)]
    [status.wait() for status in statuses]
    assert ion_chamber.sensitivity.sens_value.get(use_monitor=False).readback == 2
    assert ion_chamber.sensitivity.sens_unit.get(use_monitor=False).readback == 1
    # Change the gain without changing units
    ion_chamber.increase_gain().wait()
    assert ion_chamber.sensitivity.sens_value.get(use_monitor=False).readback == 1
    assert ion_chamber.sensitivity.sens_unit.get(use_monitor=False).readback == 1
    ion_chamber.decrease_gain().wait()
    assert ion_chamber.sensitivity.sens_value.get(use_monitor=False).readback == 2
    assert ion_chamber.sensitivity.sens_unit.get(use_monitor=False).readback == 1
    # Change the gain so that it overflows and we have to change units
    max_sensitivity = len(ion_chamber.sensitivity.values) - 1
    max_unit = len(ion_chamber.sensitivity.units) - 1
    ion_chamber.sensitivity.sens_value.set(max_sensitivity).wait()
    assert ion_chamber.sensitivity.sens_value.get(use_monitor=False).readback == 8
    ion_chamber.decrease_gain().wait()
    assert ion_chamber.sensitivity.sens_value.get(use_monitor=False).readback == 0
    assert ion_chamber.sensitivity.sens_unit.get(use_monitor=False).readback == 2
    # Check that the gain can't overflow the acceptable values
    ion_chamber.sensitivity.sens_value.set(0).wait()
    ion_chamber.sensitivity.sens_unit.set(0).wait()
    with pytest.raises(exceptions.GainOverflow):
        ion_chamber.increase_gain()
    ion_chamber.sensitivity.sens_value.set(0).wait()
    ion_chamber.sensitivity.sens_unit.set(max_unit).wait()
    with pytest.raises(exceptions.GainOverflow):
        ion_chamber.decrease_gain()
