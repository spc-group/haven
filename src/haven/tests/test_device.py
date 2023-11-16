import pytest
from ophyd import EpicsMotor, sim

from haven.instrument.device import make_device
from haven.instrument.load_instrument import load_simulated_devices
from haven.instrument.motor import HavenMotor


def test_load_simulated_devices(sim_registry):
    load_simulated_devices()
    # Check motors
    motor = sim_registry.find(name="sim_motor")
    # Check detectors
    detector = sim_registry.find(name="sim_detector")


@pytest.mark.asyncio
async def test_load_fake_device(sim_registry):
    """Does ``make_device`` create a fake device if beamline is disconnected?"""
    motor = await make_device(HavenMotor, name="real_motor")
    assert isinstance(motor.user_readback, sim.SynSignal)


@pytest.mark.asyncio
async def test_accept_fake_device(sim_registry):
    """Does ``make_device`` use a specific fake device if beamline is disconnected?"""
    FakeMotor = sim.make_fake_device(EpicsMotor)
    motor = await make_device(HavenMotor, name="real_motor", FakeDeviceClass=FakeMotor)
    assert isinstance(motor, FakeMotor)
