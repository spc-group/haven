import unittest
import warnings
import logging

import numpy as np
from ophyd import sim

from run_engine import RunEngineStub
from haven import align_slits, energy_scan, ERange, KRange


logging.basicConfig(level=logging.INFO)


def my_callback(name, doc):
    print(name, doc)


class PlanUnitTests(unittest.TestCase):
    """Unit tests for the beamline-specific plans.

    These tests do not require connected IOC's and are expected not to
    modify actual motor PVs, etc. Integration tests are run
    else-where.

    """

    RE = RunEngineStub(call_returns_result=True)


class AlignSlitsTests(PlanUnitTests):
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


class EnergyScanTests(PlanUnitTests):
    energies = np.linspace(8300, 8500, 100)
    exposure_time = 1e-3

    def test_energy_scan_basics(self):
        # Set up fake detectors and motors
        mono_motor = sim.SynAxis(name="mono_energy", labels={"motors", "energies"})
        id_gap_motor = sim.SynAxis(name="id_gap_energy", labels={"motors", "energies"})
        I0_exposure = sim.SynAxis(
            name="I0_exposure",
            labels={
                "exposures",
            },
        )
        It_exposure = sim.SynAxis(
            name="It_exposure",
            labels={
                "exposures",
            },
        )
        I0 = sim.SynGauss(
            name="I0",
            motor=mono_motor,
            motor_field="mono_energy",
            center=np.median(self.energies),
            Imax=1,
            sigma=1,
            labels={"detectors"},
        )
        It = sim.SynSignal(
            func=lambda: 1.0,
            name="It",
            exposure_time=self.exposure_time,
        )
        # Execute the plan
        scan = energy_scan(
            self.energies,
            detectors=[I0, It],
            exposure=self.exposure_time,
            energy_positioners=[mono_motor, id_gap_motor],
            time_positioners=[I0_exposure, It_exposure],
        )
        result = self.RE(scan)
        # Check that the mono and ID gap ended up in the right position
        self.assertEqual(mono_motor.get().readback, np.max(self.energies))
        self.assertEqual(id_gap_motor.get().readback, np.max(self.energies))
        self.assertEqual(I0_exposure.get().readback, self.exposure_time)
        self.assertEqual(It_exposure.get().readback, self.exposure_time)

    def test_raises_on_empty_positioners(self):
        with self.assertRaises(ValueError):
            self.RE(energy_scan(self.energies))
