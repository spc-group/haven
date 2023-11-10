import epics

from haven.instrument import motor


def test_load_vme_motors(sim_registry, mocker):
    # Mock the caget calls used to get the motor name
    mocked_caget = mocker.patch.object(motor, "caget")
    mocked_caget.side_effect = ["SLT V Upper", "SLT V Lower", "SLT H Inbound"]
    # Load the Ophyd motor definitions
    motor.load_all_motors()
    # Were the motors imported correctly
    motors = list(sim_registry.findall(label="motors"))
    assert len(motors) == 3
    # assert type(motors[0]) is motor.HavenMotor
    motor_names = [m.name for m in motors]
    assert "SLT V Upper" in motor_names
    assert "SLT V Lower" in motor_names
    assert "SLT H Inbound" in motor_names
    # Check that the IOC name is set in labels
    motor1 = sim_registry.find(name="SLT V Upper")
    assert "VME_crate" in motor1._ophyd_labels_


def test_motor_signals():
    m = motor.HavenMotor("motor_ioc", name="test_motor")
    assert m.description.pvname == "motor_ioc.DESC"
    assert m.tweak_value.pvname == "motor_ioc.TWV"
    assert m.tweak_forward.pvname == "motor_ioc.TWF"
    assert m.tweak_reverse.pvname == "motor_ioc.TWR"
    assert m.soft_limit_violation.pvname == "motor_ioc.LVIO"
