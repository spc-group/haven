from ophyd.sim import motor

from haven import set_energy

def test_plan_messages():
    """Check that the right messages are getting produced."""
    plan = set_energy(energy=8400, positioners=[motor])
    msgs = list(plan)
    assert len(msgs) == 2
    msg0 = msgs[0]
    assert msg0.args == (8400,)
    assert msg0.obj.name == "motor"
