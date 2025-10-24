import pytest
from bluesky import plan_stubs as bps


@pytest.mark.beamline()
def test_motor(startup):
    RE = startup.RE
    sim_motor_2 = startup.devices["sim_motor_2"]
    RE(startup.mv(sim_motor_2, 5))
    result = RE(bps.rd(sim_motor_2))
    RE(startup.mv(sim_motor_2, -5))
    result = RE(bps.rd(sim_motor_2))
    print(result)
    assert False
