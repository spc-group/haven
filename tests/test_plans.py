import unittest
import warnings
import logging

from run_engine import RunEngineStub
from haven import align_slits
from ophyd import sim


logging.basicConfig(level=logging.INFO)


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

    def test_warn_poor_fit(self):
        """Check that the plan emits a warning when no good fit is detected."""
        # Prepare a fake detector and slit motor
        slit_motor = sim.motor
        I0 = sim.SynGauss(
            "det",
            sim.motor,
            "motor",
            center=-0.5,
            noise="poisson",
            noise_multiplier=100,
            Imax=1,
            sigma=1,
            labels={"detectors"},
        )
        # Execute the plan, catching warnings
        with warnings.catch_warnings(record=True) as w:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            self.RE(align_slits(slit_motors=[slit_motor], ion_chamber=I0))
            # Check that a warning was raised
            self.assertEqual(len(w), 1)
            self.assertIn("Poor fit while centering motor", str(w[0].message))
