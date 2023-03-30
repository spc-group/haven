import pytest
from ophyd.sim import motor, motor1, motor2

from haven import set_energy, exceptions


def test_plan_messages():
    """Check that the right messages are getting produced."""
    plan = set_energy(energy=8400, positioners=[motor])
    msgs = list(plan)
    assert len(msgs) == 2
    msg0 = msgs[0]
    assert msg0.args == (8400,)
    assert msg0.obj.name == "motor"


def test_id_harmonic():
    """See if messages get emitted to change the ID harmonic at
    certain intervals.
    
    """
    plan = set_energy(energy=8400, harmonic=3, positioners=[motor1], harmonic_positioners=[motor2])
    msgs = list(plan)
    # Check that a message exists to the ID harmonic
    assert len(msgs) == 4
    msg0 = msgs[0]
    assert msg0.args == (3,)
    assert msg0.obj.name == "motor2"

def test_id_harmonic_auto():
    plan = set_energy(energy=8400, harmonic="auto",
                      positioners=[motor1], harmonic_positioners=[motor2])
    msgs = list(plan)
    # Check that a message exists to the ID harmonic
    assert len(msgs) == 4
    msg0 = msgs[0]
    assert msg0.args == (1,)
    assert msg0.obj.name == "motor2"
    # Try again but with a 3rd harmonic
    plan = set_energy(energy=18400, harmonic="auto",
                      positioners=[motor1], harmonic_positioners=[motor2])
    msgs = list(plan)
    # Check that a message exists to the ID harmonic
    assert len(msgs) == 4
    msg0 = msgs[0]
    assert msg0.args == (3,)
    assert msg0.obj.name == "motor2"
    
def test_invalid_harmonic():
    plan = set_energy(energy=8400, harmonic="jabberwocky",
                      positioners=[motor1], harmonic_positioners=[motor2])
    with pytest.raises(exceptions.InvalidHarmonic):
        list(plan)
