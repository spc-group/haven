import unittest
import time

from run_engine import RunEngineStub
from haven import align_slits
from ophyd import sim


def my_callback(name, doc):
    print(name, doc)


class PlanUnitTests(unittest.TestCase):
    """Unit tests for the beamline-specific plans.

    These tests do not require connected IOC's and are expected not to
    modify actual motor PVs, etc. Integration tests are run
    else-where.

    """

    RE = RunEngineStub()

    def test_align_slits(self):
        """Check the plan to aligns the slits."""
        # Prepare a fake detector and slit motor
        slit_motor = sim.motor
        I0 = sim.SynGauss(
            "det",
            sim.motor,
            "motor",
            center=-0.5,
            Imax=1,
            sigma=1,
            labels={"detectors"},
        )
        # Execute the plan
        self.RE(align_slits(slit_motors=[slit_motor], ion_chamber=I0))
        # Check that the slit positions have been set
        self.assertEqual(slit_motor.position, -0.5)
