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


@pytest.mark.beamline()
def test_asymmetric_analyzer_energy_readback(startup):
    RE = startup.RE
    analyzer = startup.devices["herfd_analyzer"]
    mv = startup.mv
    RE(
        mv(
            analyzer.surface_plane,
            (9, 1, 1),
            analyzer.reflection,
            (6, 2, 0),
            analyzer.lattice_constant,
            5.43095,
            analyzer.crystal_yaw,
            108.23,
            analyzer.crystal_pitch,
            90.434,
            analyzer.chord,
            503785.54114,
        )
    )
    # Now read the
    result = RE(startup.rd(analyzer.energy))
    assert result.plan_result == pytest.approx(7415.6, abs=2)
