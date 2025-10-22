from unittest import mock

import pytest
from bluesky import RunEngine
from ophyd_async.epics.motor import Motor

from haven.units import read_quantity, read_units, ureg


@pytest.fixture()
async def motor():
    motor = Motor("", name="motor")
    await motor.connect(mock=True)
    return motor


@pytest.fixture()
def units_task():
    task = mock.MagicMock()
    task.result.return_value = {"motor": {"units": "um"}}
    task.exception.return_value = None
    return task


@pytest.mark.slow
def test_read_no_units(motor, units_task):
    # Do this in the run engine so that at least one test calls the
    # inner `describe()`
    RE = RunEngine(call_returns_result=True)
    plan = read_units(motor)
    with pytest.raises(KeyError):
        result = RE(plan)


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
