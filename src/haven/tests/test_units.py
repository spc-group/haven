from unittest import mock

import pytest
from ophyd_async.epics.motor import Motor

from haven.units import read_quantity, read_units, ureg


@pytest.fixture()
def motor():
    motor = Motor("", name="motor")
    return motor


@pytest.fixture()
def units_task():
    task = mock.MagicMock()
    task.result.return_value = {"motor": {"units": "um"}}
    task.exception.return_value = None
    return task


def test_read_units(motor, units_task):
    plan = read_units(motor)
    next(plan)
    try:
        plan.send([units_task])
    except StopIteration as exc:
        assert exc.value == ureg.um


def test_read_quantity(motor, units_task):
    plan = read_quantity(motor)
    next(plan)
    plan.send({"readback": 2.5})
    try:
        plan.send([units_task])
    except StopIteration as exc:
        assert exc.value == ureg("2.5 um")
    else:
        raise AssertionError("Plan did not end as expected")
