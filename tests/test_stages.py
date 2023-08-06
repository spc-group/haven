import time
from unittest import mock
from collections import OrderedDict
import pytest
from ophyd import StatusBase
from ophyd.sim import instantiate_fake_device, make_fake_device
import numpy as np
from datetime import datetime

from haven import registry, exceptions
from haven.instrument import stage


@pytest.fixture()
def sim_aerotech_flyer():
    Flyer = make_fake_device(
        stage.AerotechFlyer,
    )
    flyer = Flyer(
        name="flyer",
        axis="@0",
        encoder=6,
    )
    flyer.user_setpoint._limits = (0, 1000)
    flyer.send_command = mock.MagicMock()
    yield flyer


def test_stage_init():
    stage_ = stage.XYStage(
        "motor_ioc", pv_vert=":m1", pv_horiz=":m2", labels={"stages"}, name="aerotech"
    )
    assert stage_.name == "aerotech"
    assert stage_.vert.name == "aerotech_vert"
    # Check registry of the stage and the individiual motors
    registry.clear()
    with pytest.raises(exceptions.ComponentNotFound):
        registry.findall(label="motors")
    with pytest.raises(exceptions.ComponentNotFound):
        registry.findall(label="stages")
    registry.register(stage_)
    assert len(list(registry.findall(label="motors"))) == 2
    assert len(list(registry.findall(label="stages"))) == 1


def test_load_aerotech_stage(monkeypatch):
    monkeypatch.setattr(stage, "await_for_connection", mock.AsyncMock())
    stage.load_stages()
    # Make sure these are findable
    stage_ = registry.find(name="Aerotech")
    assert stage_ is not None
    vert_ = registry.find(name="Aerotech_vert")
    assert vert_ is not None


def test_aerotech_flyer():
    aeroflyer = stage.AerotechFlyer(name="aerotech_flyer", axis="@0", encoder=6)
    assert aeroflyer is not None


def test_aerotech_stage():
    fly_stage = stage.AerotechFlyStage(
        "motor_ioc", pv_vert=":m1", pv_horiz=":m2", labels={"stages"}, name="aerotech"
    )
    assert fly_stage is not None
    assert fly_stage.asyn.ascii_output.pvname == "motor_ioc:asynEns.AOUT"


def test_aerotech_fly_params_forward(sim_aerotech_flyer):
    flyer = sim_aerotech_flyer
    # Set some example positions
    flyer.motor_egu.set("micron").wait()
    flyer.acceleration.set(0.5).wait()  # sec
    flyer.encoder_resolution.set(0.001).wait()  # µm
    flyer.start_position.set(10.05).wait()  # µm
    flyer.end_position.set(19.95).wait()  # µm
    flyer.step_size.set(0.1).wait()  # µm
    flyer.dwell_time.set(1).wait()  # sec

    # Check that the fly-scan parameters were calculated correctly
    assert flyer.pso_start.get(use_monitor=False) == 10.0
    assert flyer.pso_end.get(use_monitor=False) == 20.0
    assert flyer.slew_speed.get(use_monitor=False) == 0.1  # µm/sec
    assert flyer.taxi_start.get(use_monitor=False) == 9.9625  # µm
    assert flyer.taxi_end.get(use_monitor=False) == 20.0375  # µm
    assert flyer.encoder_step_size.get(use_monitor=False) == 100
    assert flyer.encoder_window_start.get(use_monitor=False) == -5
    assert flyer.encoder_window_end.get(use_monitor=False) == 10005
    i = 10.05
    pixel = []
    while i <= 19.98:
        pixel.append(i)
        i = i + 0.1
    np.testing.assert_allclose(flyer.pixel_positions, pixel)


def test_aerotech_fly_params_reverse(sim_aerotech_flyer):
    flyer = sim_aerotech_flyer
    # Set some example positions
    flyer.motor_egu.set("micron").wait()
    flyer.acceleration.set(0.5).wait()  # sec
    flyer.encoder_resolution.set(0.001).wait()  # µm
    flyer.start_position.set(19.95).wait()  # µm
    flyer.end_position.set(10.05).wait()  # µm
    flyer.step_size.set(0.1).wait()  # µm
    flyer.dwell_time.set(1).wait()  # sec

    # Check that the fly-scan parameters were calculated correctly
    assert flyer.pso_start.get(use_monitor=False) == 20.0
    assert flyer.pso_end.get(use_monitor=False) == 10.0
    assert flyer.slew_speed.get(use_monitor=False) == 0.1  # µm/sec
    assert flyer.taxi_start.get(use_monitor=False) == 20.0375  # µm
    assert flyer.taxi_end.get(use_monitor=False) == 9.9625  # µm
    assert flyer.encoder_step_size.get(use_monitor=False) == 100
    assert flyer.encoder_window_start.get(use_monitor=False) == 5
    assert flyer.encoder_window_end.get(use_monitor=False) == -10005

    i = 19.95
    pixel = []
    while i >= 10.03:
        pixel.append(i)
        i = i - 0.1
    np.testing.assert_allclose(flyer.pixel_positions, pixel)


def test_aerotech_fly_params_no_window(sim_aerotech_flyer):
    """Test the fly scan params when the range is too large for the PSO window."""
    flyer = sim_aerotech_flyer
    # Set some example positions
    flyer.motor_egu.set("micron").wait()
    flyer.acceleration.set(0.5).wait()  # sec
    flyer.encoder_resolution.set(0.001).wait()  # µm
    flyer.start_position.set(0).wait()  # µm
    flyer.end_position.set(9000).wait()  # µm
    flyer.step_size.set(0.1).wait()  # µm
    flyer.dwell_time.set(1).wait()  # sec

    # Check that the fly-scan parameters were calculated correctly
    assert flyer.pso_start.get(use_monitor=False) == -0.05
    assert flyer.pso_end.get(use_monitor=False) == 9000.05
    assert flyer.taxi_start.get(use_monitor=False) == pytest.approx(-0.0875)  # µm
    assert flyer.taxi_end.get(use_monitor=False) == 9000.0875  # µm
    assert flyer.encoder_step_size.get(use_monitor=False) == 100
    assert flyer.encoder_window_start.get(use_monitor=False) is -5
    assert flyer.encoder_window_end.get(use_monitor=False) is None


def test_enable_pso(sim_aerotech_flyer):
    flyer = sim_aerotech_flyer
    # Set up scan parameters
    flyer.encoder_step_size.set(50).wait()  # In encoder counts
    flyer.encoder_window_start.set(-5).wait()  # In encoder counts
    flyer.encoder_window_end.set(10000).wait()  # In encoder counts
    # Check that commands are sent to set up the controller for flying
    flyer.enable_pso()
    assert flyer.send_command.called
    commands = [c.args[0] for c in flyer.send_command.call_args_list]
    assert commands == [
        "PSOCONTROL @0 RESET",
        "PSOOUTPUT @0 CONTROL 1",
        "PSOPULSE @0 TIME 20, 10",
        "PSOOUTPUT @0 PULSE WINDOW MASK",
        "PSOTRACK @0 INPUT 6",
        "PSODISTANCE @0 FIXED 50",
        "PSOWINDOW @0 1 INPUT 6",
        "PSOWINDOW @0 1 RANGE -5,10000",
    ]


def test_enable_pso_no_window(sim_aerotech_flyer):
    flyer = sim_aerotech_flyer
    # Set up scan parameters
    flyer.encoder_step_size.set(50).wait()  # In encoder counts
    flyer.encoder_window_start.set(-5).wait()  # In encoder counts
    flyer.encoder_window_end.set(None).wait()  # High end is outside the window range
    # Check that commands are sent to set up the controller for flying
    flyer.enable_pso()
    assert flyer.send_command.called
    commands = [c.args[0] for c in flyer.send_command.call_args_list]
    assert commands == [
        "PSOCONTROL @0 RESET",
        "PSOOUTPUT @0 CONTROL 1",
        "PSOPULSE @0 TIME 20, 10",
        "PSOOUTPUT @0 PULSE",
        "PSOTRACK @0 INPUT 6",
        "PSODISTANCE @0 FIXED 50",
        # "PSOWINDOW @0 1 INPUT 6",
        # "PSOWINDOW @0 1 RANGE -5,10000",
    ]


def test_pso_bad_window_forward(sim_aerotech_flyer):
    """Check for an exception when the window is needed but not enabled.

    I.e. when the taxi distance is larger than the encoder step size."""
    flyer = sim_aerotech_flyer
    # Set up scan parameters
    flyer.encoder_resolution.set(1).wait()
    flyer.encoder_step_size.set(
        5 / flyer.encoder_resolution.get()
    ).wait()  # In encoder counts
    flyer.encoder_window_start.set(-5).wait()  # In encoder counts
    flyer.encoder_window_end.set(None).wait()  # High end is outside the window range
    flyer.pso_end.set(100)
    flyer.taxi_end.set(110)
    # Check that commands are sent to set up the controller for flying
    with pytest.raises(exceptions.InvalidScanParameters):
        flyer.enable_pso()


def test_pso_bad_window_reverse(sim_aerotech_flyer):
    """Check for an exception when the window is needed but not enabled.

    I.e. when the taxi distance is larger than the encoder step size."""
    flyer = sim_aerotech_flyer
    # Set up scan parameters
    flyer.encoder_resolution.set(1).wait()
    flyer.step_size.set(5).wait()
    flyer.encoder_step_size.set(
        flyer.step_size.get() / flyer.encoder_resolution.get()
    ).wait()  # In encoder counts
    flyer.encoder_window_start.set(114).wait()  # In encoder counts
    flyer.encoder_window_start.set(None).wait()  # High end is outside the window range
    flyer.pso_start.set(100)
    flyer.taxi_start.set(94)
    # Check that commands are sent to set up the controller for flying
    with pytest.raises(exceptions.InvalidScanParameters):
        flyer.enable_pso()


def test_arm_pso(sim_aerotech_flyer):
    flyer = sim_aerotech_flyer
    assert not flyer.send_command.called
    flyer.arm_pso()
    assert flyer.send_command.called
    command = flyer.send_command.call_args.args[0]
    assert command == "PSOCONTROL @0 ARM"


def test_motor_units(sim_aerotech_flyer):
    """Check that the motor and flyer handle enginering units properly."""
    flyer = sim_aerotech_flyer
    flyer.motor_egu.set("micron").wait()
    unit = flyer.motor_egu_pint
    assert unit == stage.ureg("1e-6 m")


def test_kickoff(sim_aerotech_flyer):
    # Set up fake flyer with mocked fly method
    flyer = sim_aerotech_flyer
    flyer.taxi = mock.MagicMock()
    # Start flying
    status = flyer.kickoff()
    # Check status behavior matches flyer interface
    assert isinstance(status, StatusBase)
    assert not status.done
    # Start flying and see if the status is done
    flyer.ready_to_fly.set(True).wait()
    status.wait()
    assert status.done
    assert type(flyer.starttime) == float


def test_complete(sim_aerotech_flyer):
    # Set up fake flyer with mocked fly method
    flyer = sim_aerotech_flyer
    flyer.move = mock.MagicMock()
    flyer.is_flying.set(False).wait()
    assert flyer.user_setpoint.get() == 0
    flyer.taxi_end.set(10).wait()
    # Complete flying
    status = flyer.complete()
    # Check that the motor was moved
    assert flyer.move.called_with(9)
    # Check status behavior matches flyer interface
    assert isinstance(status, StatusBase)
    status.wait()
    assert status.done


def test_collect(sim_aerotech_flyer):
    flyer = sim_aerotech_flyer
    # Set up needed parameters
    flyer.pixel_positions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    flyer.starttime = 0
    flyer.endtime = flyer.starttime + 11.25
    motor_accel = flyer.acceleration.set(0.5).wait()  # µm/s^2
    flyer.step_size.set(0.1).wait()  # µm
    flyer.dwell_time.set(1).wait()  # sec
    expected_timestamps = [
        1.125,
        2.125,
        3.125,
        4.125,
        5.125,
        6.125,
        7.125,
        8.125,
        9.125,
        10.125,
    ]
    payload = list(flyer.collect())
    # Confirm data have the right structure
    for datum, value, timestamp in zip(
        payload, flyer.pixel_positions, expected_timestamps
    ):
        assert datum == {
            "data": {"flyer": value},
            "timestamps": {"flyer": timestamp},
            "time": timestamp,
        }


def test_describe_collect(sim_aerotech_flyer):
    expected = {
        "primary": OrderedDict(
            [
                (
                    "flyer",
                    {
                        "source": "SIM:flyer",
                        "dtype": "integer",
                        "shape": [],
                        "precision": 3,
                    },
                ),
                (
                    "flyer_user_setpoint",
                    {
                        "source": "SIM:flyer_user_setpoint",
                        "dtype": "integer",
                        "shape": [],
                        "precision": 3,
                    },
                ),
            ]
        )
    }

    assert sim_aerotech_flyer.describe_collect()["primary"] == expected["primary"]


def test_fly_motor_positions(sim_aerotech_flyer):
    flyer = sim_aerotech_flyer
    # Arbitrary rest position
    flyer.user_setpoint.set(255)
    # Set example fly scan parameters
    flyer.taxi_start.set(5)
    flyer.start_position.set(10)
    flyer.pso_start.set(9.5)
    flyer.taxi_end.set(105)
    # Mock the motor position so that it returns a status we control
    motor_status = StatusBase()
    motor_status.set_finished()
    mover = mock.MagicMock(return_value=motor_status)
    flyer.move = mover
    # Check the fly scan moved the motors in the right order
    flyer.taxi()
    flyer.fly()
    assert mover.called
    positions = [c.args[0] for c in mover.call_args_list]
    assert len(positions) == 3
    pso_start, taxi, end = positions
    assert pso_start == 9.5
    assert taxi == 5
    assert end == 105


def test_aerotech_move_status(sim_aerotech_flyer):
    """Check that the flyer only finishes when the readback value is reached."""
    flyer = sim_aerotech_flyer
    status = flyer.move(100, wait=False)
    assert not status.done
    # To-Do: figure out how to make this be done in the fake device
    # assert status.done
