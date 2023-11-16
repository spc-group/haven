"""Tests for a generic X-Y stage."""


import pytest

from haven import exceptions, registry
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
