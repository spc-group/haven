import time

import matplotlib.pyplot as plt
import pytest
from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.callbacks.fitting import PeakStats
from ophyd import sim

from haven import align_motor, align_pitch2, registry

# from run_engine import RunEngineStub


@pytest.mark.skip(reason="Deprecated, use bluesky.plans.tune_centroid")
def test_align_motor(ffapp):
    # Set up simulated motors and detectors
    motor = sim.SynAxis(name="motor", labels={"motors"})
    detector = sim.SynGauss(
        name="detector",
        motor=motor,
        motor_field="motor",
        center=-3,
        Imax=1,
        sigma=20,
        labels={"detectors"},
    )
    # Prepare the callback to check results
    bec = BestEffortCallback()
    bec.disable_plots()
    bec.disable_table()
    # Prepare the plan
    plan = align_motor(
        detector=detector,
        motor=motor,
        distance=40,
        bec=bec,
        md={"plan_name": "test_plan"},
    )
    # Execute the plan
    RE = RunEngine(call_returns_result=True)
    result = RE(plan)
    # Check peak calculation results
    assert bec.peaks["cen"]["detector"] == pytest.approx(-3, rel=1e-3)
    assert motor.readback.get() == pytest.approx(-3, rel=1e-3)


# def test_align_pitch2():
#     # Prepare fake motors
#     motor = registry.register(sim.SynAxis(name="monochromator_pitch2", labels={"motors"}))
#     detector = registry.register(sim.SynGauss(
#         name="I0",
#         motor=motor,
#         motor_field="monochromator_pitch2",
#         center=-3,
#         Imax=1,
#         sigma=20,
#         labels={"detectors"},
#     ))
#     # Prepare the callback to check results
#     bec = BestEffortCallback()
#     bec.disable_plots()
#     bec.disable_table()
#     # Prepare the plan
#     plan = align_pitch2(bec=bec, distance=40, reverse=True)
#     # Execute the plan
#     RE = RunEngineStub(call_returns_result=True)
#     result = RE(plan)
#     # Check that the pitch motor gets moved
#     assert "I0" in bec.peaks['cen'].keys()
#     assert bec.peaks['cen']['I0'] == pytest.approx(-3, rel=1e-3)
#     assert motor.readback.get() == pytest.approx(-3, rel=1e-3)
