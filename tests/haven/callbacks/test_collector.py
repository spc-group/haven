import numpy as np
import pytest
from bluesky import RunEngine
from bluesky import plans as bp
from bluesky import preprocessors as bpp
from ophyd_async import sim
from ophyd_async.core import init_devices

from haven.callbacks import Collector


@pytest.fixture()
def RE():
    RE_ = RunEngine({})
    return RE_


@pytest.fixture()
def devices(RE):
    pattern_generator = sim.PatternGenerator()
    with init_devices():
        motor = sim.SimMotor(instant=True)
        det = sim.SimPointDetector(pattern_generator)
    return [motor, det]


def test_collector_collects(RE, devices):
    motor, det = devices
    collector = Collector()
    collector.reset()  # Reset just to check that it works
    plan = bp.scan([det], motor, -5, 5, 21)
    plan = bpp.subs_wrapper(plan, collector)
    RE(plan)
    # Check collected values
    np.testing.assert_equal(collector[motor.name], np.linspace(-5, 5, num=21))
