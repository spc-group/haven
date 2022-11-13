import pytest

from haven import registry, exceptions
from haven.instrument import stage
from test_simulated_ioc import ioc_motor


def test_stage_init():
    stage_ = stage.XYStage("motor_ioc", pv_vert=":m1", pv_horiz=":m2", labels={"stages"}, name="aerotech")
    assert stage_.name == "aerotech"
    assert stage_.vert.name == "aerotech_vert"
    # Check registry of the stage and the individiual motors
    registry.clear()
    with pytest.raises(exceptions.ComponentNotFound):
        registry.findall(label="motors")
    with pytest.raises(exceptions.ComponentNotFound):
        registry.findall(label="stages")
    registry.register(stage_)
    assert len(registry.findall(label="motors")) == 2
    assert len(registry.findall(label="stages")) == 1


def test_load_aerotech_stage():
    stage.load_stages()
    stage_ = registry.find(name="Aerotech")
    vert = registry.find(name="Aerotech_vert")
