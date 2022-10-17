import pytest

from haven.instrument import IonChamber

from simulated_ioc import ioc_ion_chamber


def test_gain_changes(ioc_ion_chamber):
    ion_chamber = IonChamber(prefix="vme_crate_ioc", preamp_prefix="preamp_ioc", ch_num=2, name="ion_chamber")
    # Check that it respects the default value in the IOC
    assert ion_chamber.sensitivity == 5
    assert ion_chamber.sensitivity_unit == "nA/V"
    # Now change the gain without changing units
    for status in ion_chamber.increase_gain():
        status.wait()
    assert ion_chamber.sensitivity == 2
    assert ion_chamber.sensitivity_unit == "nA/V"
    for status in ion_chamber.decrease_gain():
        status.wait()
    assert ion_chamber.sensitivity == 5
    # Change the gain so that it overflows and we have to change units
    max_sensitivity = len(ion_chamber.sensitivities)-1
    ion_chamber._sensitivity.set(max_sensitivity).wait()
    for status in ion_chamber.decrease_gain():
        status.wait()
    assert ion_chamber.sensitivity == 1
    assert ion_chamber.sensitivity_unit == "µA/V"

