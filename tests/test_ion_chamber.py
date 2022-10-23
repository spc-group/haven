import pytest
import time

from haven.instrument.ion_chamber import IonChamber, SensitivityLevelPositioner
from haven import exceptions
import epics

from test_simulated_ioc import ioc_ion_chamber, ioc_scaler


def test_gain_level(ioc_ion_chamber):
    print(ioc_ion_chamber)
    positioner = SensitivityLevelPositioner("preamp_ioc", name="positioner")
    print(positioner.sens_unit.prefix)
    print(ioc_ion_chamber)
    positioner.wait_for_connection()
    assert positioner.get().sens_value.readback == epics.caget(
        "preamp_ioc:sens_num.VAL"
    )
    assert positioner.get().sens_unit.readback == epics.caget(
        "preamp_ioc:sens_unit.VAL"
    )
    # Move the gain level
    positioner.sens_level.set(12)
    time.sleep(0.1)  # Caproto breaks pseudopositioner status
    # Check that the preamp sensitivities are moved
    assert positioner.get().sens_value.readback == 3
    assert positioner.get().sens_unit.readback == 1
    # Change the preamp settings
    epics.caput("preamp_ioc:sens_num.VAL", 0)
    epics.caput("preamp_ioc:sens_unit.VAL", 3)
    time.sleep(0.1)
    # Check that the gain level moved
    assert positioner.sens_level.get().readback == 27


def test_gain_changes(ioc_ion_chamber, ioc_scaler):
    ion_chamber = IonChamber(
        prefix="vme_crate_ioc", preamp_prefix="preamp_ioc", ch_num=2, name="ion_chamber"
    )
    # print(ion_chamber.sensitivity.unit.prefix, ioc_ion_chamber)

    ion_chamber.wait_for_connection(5)
    # Check that it respects the default value in the IOC
    assert ion_chamber.sensitivity.sens_value.get().readback == 2
    assert ion_chamber.sensitivity.sens_unit.get().readback == 1
    # Now change the gain without changing units
    ion_chamber.increase_gain().wait()
    assert ion_chamber.sensitivity.sens_value.get().readback == 1
    assert ion_chamber.sensitivity.sens_unit.get().readback == 1
    ion_chamber.decrease_gain().wait()
    assert ion_chamber.sensitivity.sens_value.get().readback == 2
    assert ion_chamber.sensitivity.sens_unit.get().readback == 1
    # Change the gain so that it overflows and we have to change units
    max_sensitivity = len(ion_chamber.sensitivity.values) - 1
    max_unit = len(ion_chamber.sensitivity.units) - 1
    ion_chamber.sensitivity.sens_value.set(max_sensitivity).wait()
    assert ion_chamber.sensitivity.sens_value.get().readback == 8
    ion_chamber.decrease_gain().wait()
    assert ion_chamber.sensitivity.sens_value.get().readback == 0
    assert ion_chamber.sensitivity.sens_unit.get().readback == 2
    # Check that the gain can't overflow the acceptable values
    ion_chamber.sensitivity.sens_value.set(0).wait()
    ion_chamber.sensitivity.sens_unit.set(0).wait()
    with pytest.raises(exceptions.GainOverflow):
        ion_chamber.increase_gain()
    ion_chamber.sensitivity.sens_value.set(0).wait()
    ion_chamber.sensitivity.sens_unit.set(max_unit).wait()
    with pytest.raises(exceptions.GainOverflow):
        ion_chamber.decrease_gain()
