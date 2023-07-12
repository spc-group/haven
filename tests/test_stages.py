from unittest import mock
import pytest

from haven import registry, exceptions
from haven.instrument import stage


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


def test_load_aerotech_stage():
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


def test_aerotech_slew_speed():
    flyer = stage.AerotechFlyer(name="flyer", axis="@0", encoder=0)
    # Set some example positions
    flyer.motor_egu.set("micron").wait()
    flyer.start_position.set(10).wait()
    flyer.end_position.set(20).wait()
    flyer.step_size.set(0.1).wait()
    flyer.dwell_time.set(1).wait()
    assert flyer.slew_speed.get(use_monitor=False) == 0.1


def test_enable_pso():
    flyer = stage.AerotechFlyer(name="flyer", axis="@0", encoder=6)
    flyer.send_command = mock.MagicMock()
    # Set up scan parameters
    flyer.encoder_step_size.set(50).wait()   # In encoder counts
    flyer.taxi_start.set(-0.025).wait()  # In encoder counts
    flyer.taxi_end.set(9999.975).wait()  # In encoder counts
    # Check that commands are sent to set up the controller for flying
    flyer.enable_pso()
    assert flyer.send_command.called
    commands = [c.args[0] for c in flyer.send_command.call_args_list]
    assert commands == [
        "PSOCONTROL @0 RESET",
        "PSOOUTPUT @0 CONTROL 1",
        "PSOPULSE @0 TIME 20,10",
        "PSOOUTPUT @0 PULSE WINDOW MASK",
        "PSOTRACK @0 INPUT 6",
        "PSODISTANCE @0 FIXED 50",
        "PSOWINDOW @0 1 INPUT 6",
        "PSOWINDOW @0 1 RANGE -0.025,9999.975",
    ]
