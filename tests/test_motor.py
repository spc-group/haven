import pytest

from haven.instrument.instrument_registry import registry
from haven.instrument import motor
from test_simulated_ioc import ioc_motor


def test_load_vme_motors(ioc_motor):
    motor.load_all_motors()
    # Were the motors imported correctly
    motors = registry.findall(label="motors")
    assert len(motors) == 3
    motor_names = [m.name for m in motors]
    assert "SLT V Upper" in motor_names
    assert "SLT V Lower" in motor_names
    assert "SLT H Inb" in motor_names
