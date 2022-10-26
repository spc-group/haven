import time

import pytest
from ophyd.sim import motor1, motor2

from haven import save_motor_position


def test_save_motor_position_by_name(mongodb):
    # Check that no entry exists before saving it
    result = mongodb.motor_positions.find_one({"name": motor1.name})
    assert result is None
    # Save the current motor position
    new_id = save_motor_position(
        motor1, motor2, name="Sample center", collection=mongodb.motor_positions
    )
    # Check that the motors got saved
    result = mongodb.motor_positions.find_one({"name": "Sample center"})
    assert result is not None
