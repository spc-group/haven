import time

import epics
import pytest
from bluesky import RunEngine
from bluesky.simulators import summarize_plan
from ophyd.sim import motor1, motor2
from ophyd import EpicsMotor
from haven import (
    save_motor_position,
    registry,
    get_motor_position,
    list_motor_positions,
    recall_motor_position,
    HavenMotor,
)

from test_simulated_ioc import ioc_motor


@pytest.fixture
def sim_registry():
    # Clean the registry so we can restore it later
    components = registry.components
    registry.clear()
    # Create the motors
    pv = "vme_crate_ioc:m1"
    motor1 = EpicsMotor(pv, name="SLT V Upper")
    registry.register(motor1)
    motor2 = EpicsMotor(pv, name="SLT V Lower")
    registry.register(motor2)
    # Run the test
    yield registry
    # Restore the previous registry components
    registry.components = components


def test_save_motor_position_by_device(mongodb, ioc_motor):
    # Check that no entry exists before saving it
    result = mongodb.motor_positions.find_one({"name": motor1.name})
    assert result is None
    # Create motor devices
    motorA = HavenMotor("vme_crate_ioc:m1", name="Motor A")
    motorB = HavenMotor("vme_crate_ioc:m2", name="Motor B")
    motorA.wait_for_connection()
    motorB.wait_for_connection()
    # Move to some other motor position so we can tell it saved the right one
    motorA.set(11.0)
    motorB.set(23.0)
    time.sleep(0.1)
    # Save the current motor position
    save_motor_position(
        motorA, motorB, name="Sample center", collection=mongodb.motor_positions
    )
    # Check that the motors got saved
    result = mongodb.motor_positions.find_one({"name": "Sample center"})
    assert result is not None
    assert result["motors"][0]["name"] == motorA.name
    assert result["motors"][0]["readback"] == 11.0
    assert result["motors"][1]["readback"] == 23.0


def test_save_motor_position_by_name(mongodb, ioc_motor):
    # Check that no entry exists before saving it
    result = mongodb.motor_positions.find_one({"name": motor1.name})
    assert result is None
    # Get our simulated motors into the device registry
    motorA = HavenMotor("vme_crate_ioc:m1", name="Motor A")
    motorB = HavenMotor("vme_crate_ioc:m2", name="Motor B")
    motorA.wait_for_connection()
    motorB.wait_for_connection()
    registry.register(motorA)
    registry.register(motorB)
    # Move to some other motor position so we can tell it saved the right one
    motorA.set(11.0)
    motorA.user_offset.set(1.5)
    motorB.set(23.0)
    time.sleep(0.1)
    # Save the current motor position
    new_id = save_motor_position(
        "Motor A", "Motor B", name="Sample center", collection=mongodb.motor_positions
    )
    # Check that the motors got saved
    result = mongodb.motor_positions.find_one({"name": "Sample center"})
    assert result is not None
    assert result["motors"][0]["name"] == motorA.name
    assert result["motors"][0]["readback"] == 11.0
    assert result["motors"][1]["readback"] == 23.0
    assert result["motors"][0]["offset"] == 1.5


def test_get_motor_position_by_uid(mongodb):
    uid = str(mongodb.motor_positions.find_one({'name': "Good position A"})['_id'])
    result = get_motor_position(uid=uid, collection=mongodb.motor_positions)
    assert result.name == "Good position A"
    assert result.motors[0].name == "SLT V Upper"
    assert result.motors[0].readback == 510.5


def test_get_motor_position_by_name(mongodb):
    result = get_motor_position(name="Good position A", collection=mongodb.motor_positions)
    assert result.name == "Good position A"
    assert result.motors[0].name == "SLT V Upper"
    assert result.motors[0].readback == 510.5


def test_get_motor_position_exceptions(mongodb):
    # Fails when no query params are given
    with pytest.raises(TypeError):
        get_motor_position(collection=mongodb.motor_positions)


def test_recall_motor_position(mongodb, sim_registry):
    # Re-set the previous value
    uid = str(mongodb.motor_positions.find_one({'name': "Good position A"})['_id'])
    plan = recall_motor_position(uid=uid, collection=mongodb.motor_positions)
    messages = list(plan)
    # Check the plan output
    msg0 = messages[0]
    assert msg0.obj.name == "SLT V Upper"
    assert msg0.args[0] == 510.5
    msg1 = messages[1]
    assert msg1.obj.name == "SLT V Lower"
    assert msg1.args[0] == -211.93


def test_list_motor_positions(mongodb, capsys):
    # Do the listing
    list_motor_positions(collection=mongodb.motor_positions)
    # Check stdout for printed motor positions
    captured = capsys.readouterr()
    assert len(captured.out) > 0
    uid = str(mongodb.motor_positions.find_one({'name': "Good position A"})['_id'])
    expected = (f'\n\033[1mGood position A\033[0m (uid="{uid}")\n'
                '┣━SLT V Upper: 510.5\n'
                '┗━SLT V Lower: -211.93\n')
    assert captured.out == expected


def test_motor_position_e2e(mongodb, ioc_motor):
    """Check that a motor position can be saved, then recalled using
    simulated IOC.

    """
    # Create an epics motor for setting values manually
    pv = "vme_crate_ioc:m1"
    motor1 = EpicsMotor(pv, name="SLT V Upper")
    motor1.wait_for_connection()
    assert motor1.connected
    registry.register(motor1)
    registry.find(name="SLT V Upper")
    epics.caput(pv, 504.6)
    assert epics.caget(pv, use_monitor=False) == 504.6
    time.sleep(0.1)
    assert motor1.get(use_monitor=False).user_readback == 504.6
    # Save motor position
    uid = save_motor_position(
        motor1, name="starting point", collection=mongodb.motor_positions
    )
    # Change to a different value
    epics.caput(pv, 520)
    time.sleep(0.1)
    assert epics.caget(pv, use_monitor=False) == 520
    assert motor1.get(use_monitor=False).user_readback == 520
    # Recall the saved position and see if it complies
    RE = RunEngine()
    plan = recall_motor_position(uid=uid, collection=mongodb.motor_positions)
    msg = next(plan)
    print(msg)
    assert msg.obj.name == "SLT V Upper"
    assert msg.args[0] == 504.6
