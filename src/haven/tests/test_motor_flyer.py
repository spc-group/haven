from collections import OrderedDict

import numpy as np
import pytest
from ophyd import EpicsMotor
from ophyd.flyers import FlyerInterface
from ophyd.sim import instantiate_fake_device
from ophyd.status import StatusBase

from haven.instrument.motor_flyer import MotorFlyer


@pytest.fixture()
def motor(sim_registry, mocker):
    Motor = type("Motor", (MotorFlyer, EpicsMotor), {})
    m = instantiate_fake_device(Motor, name="m1")
    mocker.patch.object(m, "move")
    m.user_setpoint._use_limits = False
    return m


def test_motor_flyer(motor):
    """Check that the haven motor implements the flyer interface."""
    assert motor is not None
    assert isinstance(motor, FlyerInterface)


def test_fly_params_forward(motor):
    """Test that the fly-scan parameters are correct when going from
    lower to higher positions.

    """
    # Set some example positions
    motor.motor_egu.set("micron").wait(timeout=3)
    motor.acceleration.set(0.5).wait(timeout=3)  # sec
    motor.flyer_start_position.set(10.0).wait(timeout=3)  # µm
    motor.flyer_end_position.set(20.0).wait(timeout=3)  # µm
    motor.flyer_num_points.set(101).wait(timeout=3)  # µm
    motor.flyer_dwell_time.set(1).wait(timeout=3)  # sec

    # Check that the fly-scan parameters were calculated correctly
    assert motor.flyer_slew_speed.get(use_monitor=False) == pytest.approx(0.1)  # µm/sec
    assert motor.flyer_taxi_start.get(use_monitor=False) == pytest.approx(9.9125)  # µm
    assert motor.flyer_taxi_end.get(use_monitor=False) == pytest.approx(20.0875)  # µm
    i = 10.0
    pixel = []
    while i <= 20.005:
        pixel.append(i)
        i = i + 0.1
    np.testing.assert_allclose(motor.pixel_positions, pixel)


def test_fly_params_reverse(motor):
    """Test that the fly-scan parameters are correct when going from
    higher to lower positions.

    """
    # Set some example positions
    motor.motor_egu.set("micron").wait(timeout=3)
    motor.acceleration.set(0.5).wait(timeout=3)  # sec
    motor.flyer_start_position.set(20.0).wait(timeout=3)  # µm
    motor.flyer_end_position.set(10.0).wait(timeout=3)  # µm
    motor.flyer_num_points.set(101).wait(timeout=3)  # µm
    motor.flyer_dwell_time.set(1).wait(timeout=3)  # sec

    # Check that the fly-scan parameters were calculated correctly
    assert motor.flyer_slew_speed.get(use_monitor=False) == pytest.approx(0.1)  # µm/sec
    assert motor.flyer_taxi_start.get(use_monitor=False) == pytest.approx(20.0875)  # µm
    assert motor.flyer_taxi_end.get(use_monitor=False) == pytest.approx(9.9125)  # µm
    i = 20.0
    pixel = []
    while i >= 9.995:
        pixel.append(i)
        i = i - 0.1
    np.testing.assert_allclose(motor.pixel_positions, pixel)


def test_kickoff(motor):
    motor.flyer_dwell_time.put(1.0)
    motor.flyer_taxi_start.put(1.5)
    # Start flying
    status = motor.kickoff()
    # Check status behavior matches flyer interface
    assert isinstance(status, StatusBase)
    status.wait(timeout=1)
    # Make sure the motor moved to its taxi position
    motor.move.assert_called_once_with(1.5, wait=True)


def test_complete(motor):
    # Set up fake flyer with mocked fly method
    assert motor.user_setpoint.get() == 0
    motor.flyer_taxi_end.put(10)
    # Complete flying
    status = motor.complete()
    # Check that the motor was moved
    assert isinstance(status, StatusBase)
    status.wait()
    motor.move.assert_called_once_with(10, wait=True)


def test_collect(motor):
    # Set up some fake positions from camonitors
    motor._fly_data = [
        # timestamp, position
        (1.125, 0.5),
        (2.125, 1.5),
        (3.125, 2.5),
        (4.125, 3.5),
        (5.125, 4.5),
        (6.125, 5.5),
        (7.125, 6.5),
        (8.125, 7.5),
        (9.125, 8.5),
        (10.125, 9.5),
        (11.125, 10.5),
    ]
    payload = list(motor.collect())
    # Confirm data have the right structure
    for datum, (timestamp, value) in zip(payload, motor._fly_data):
        assert datum["data"] == {
            "m1": value,
            "m1_user_setpoint": value,
        }
        assert datum["timestamps"]["m1"] == pytest.approx(timestamp, abs=0.3)
        assert datum["time"] == pytest.approx(timestamp, abs=0.3)


def test_predict(motor):
    # Set up some fake positions from camonitors
    motor._fly_data = [
        # timestamp, position
        (1.125, 0.5),
        (2.125, 1.5),
        (3.125, 2.5),
        (4.125, 3.5),
        (5.125, 4.5),
        (6.125, 5.5),
        (7.125, 6.5),
        (8.125, 7.5),
        (9.125, 8.5),
        (10.125, 9.5),
        (11.125, 10.5),
    ]
    # Prepare expected timestamp and position data
    expected_positions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    motor.pixel_positions = np.asarray(expected_positions)
    expected_timestamps = [
        1.625,
        2.625,
        3.625,
        4.625,
        5.625,
        6.625,
        7.625,
        8.625,
        9.625,
        10.625,
    ]
    ts = [d[0] for d in motor._fly_data]
    vs = [d[1] for d in motor._fly_data]
    # Confirm data have the right structure
    for timestamp, expected_value in zip(expected_timestamps, expected_positions):
        datum = motor.predict(timestamp)
        assert datum["data"]["m1"] == pytest.approx(expected_value, abs=0.2)
        assert datum["data"]["m1_user_setpoint"] == expected_value
        assert datum["timestamps"]["m1"] == timestamp
        assert datum["time"] == timestamp


def test_describe_collect(aerotech_flyer):
    expected = {
        "positions": OrderedDict(
            [
                (
                    "aerotech_horiz",
                    {
                        "source": "SIM:aerotech_horiz",
                        "dtype": "integer",
                        "shape": [],
                        "precision": 3,
                    },
                ),
                (
                    "aerotech_horiz_user_setpoint",
                    {
                        "source": "SIM:aerotech_horiz_user_setpoint",
                        "dtype": "integer",
                        "shape": [],
                        "precision": 3,
                    },
                ),
            ]
        )
    }

    assert aerotech_flyer.describe_collect() == expected
