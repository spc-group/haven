import epics

from haven.instrument.instrument_registry import registry
from haven.instrument import motor


def test_load_vme_motors(ioc_motor):
    registry.clear()
    # Set the IOC motor descriptions to known values
    epics.caput('vme_crate_ioc:m1.DESC', "SLT V Upper")
    epics.caput('vme_crate_ioc:m2.DESC', "SLT V Lower")
    epics.caput('vme_crate_ioc:m3.DESC', "SLT H Inbound")
    assert epics.caget('vme_crate_ioc:m1.DESC', use_monitor=False) == "SLT V Upper"
    assert epics.caget('vme_crate_ioc:m2.DESC', use_monitor=False) == "SLT V Lower"
    assert epics.caget('vme_crate_ioc:m3.DESC', use_monitor=False) == "SLT H Inbound"
    # Load the Ophyd motor definitions
    motor.load_all_motors()
    # Were the motors imported correctly
    motors = registry.findall(label="motors")
    assert len(motors) == 3
    motor_names = [m.name for m in motors]
    assert "SLT V Upper" in motor_names
    assert "SLT V Lower" in motor_names
    assert "SLT H Inbound" in motor_names
    # Check that the IOC name is set in labels
    motor1 = registry.find(name="SLT V Upper")
    assert "VME_crate" in motor1._ophyd_labels_
