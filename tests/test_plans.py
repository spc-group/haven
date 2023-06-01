"""An assortment of tests for plans defined in Haven.

NOTE: This file uses the older unittest framework. We have since moved
to pytest, and new tests should be added to a plan-specific test file.

"""

import unittest
import warnings

import numpy as np
from ophyd import sim
import pytest

from run_engine import RunEngineStub
from haven import align_slits, energy_scan, xafs_scan, registry, KRange


class PlanUnitTests(unittest.TestCase):
    """Unit tests for the beamline-specific plans.

    These tests do not require connected IOC's and are expected not to
    modify actual motor PVs, etc. Integration tests are run
    else-where.

    """

    mono_motor = sim.SynAxis(name="mono_energy", labels={"motors", "energies"})
    exposure_motor = sim.Signal(name="exposure")
    id_gap_motor = sim.SynAxis(name="id_gap_energy", labels={"motors", "energies"})
    RE = RunEngineStub(call_returns_result=True)

    def setUp(self):
        registry.clear()
        # Register an ion chamber
        I0 = sim.SynGauss(
            "I0",
            sim.motor,
            "motor",
            center=-0.5,
            Imax=1,
            sigma=1,
            labels={"ion_chambers"},
        )
        # Register the energy positioner
        exposure_time = sim.SynAxis(name="I0_exposure_time")
        energy = sim.SynAxis(name="energy")
        for dev in [I0, exposure_time, energy]:
            registry.register(dev)


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
        assert slit_motor.position == pytest.approx(-0.5)

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
            motor=self.mono_motor,
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
            energy_positioners=[self.mono_motor, self.id_gap_motor],
            time_positioners=[I0_exposure, It_exposure],
        )
        self.RE(scan)
        # Check that the mono and ID gap ended up in the right position
        self.assertEqual(self.mono_motor.get().readback, np.max(self.energies))
        self.assertEqual(self.id_gap_motor.get().readback, np.max(self.energies))
        self.assertEqual(I0_exposure.get().readback, self.exposure_time)
        self.assertEqual(It_exposure.get().readback, self.exposure_time)

    def test_raises_on_empty_positioners(self):
        with self.assertRaises(ValueError):
            self.RE(energy_scan(self.energies, energy_positioners=[]))


class XafsScanTests(PlanUnitTests):
    E0 = 10000  # in electron-volts

    def test_single_range(self):
        expected_energies = np.arange(9990, 10001, step=1)
        expected_exposures = np.asarray([1.0])
        scan = xafs_scan(
            -10,
            1,
            1,
            0,
            E0=self.E0,
            energy_positioners=[self.mono_motor],
            time_positioners=[self.exposure_motor],
        )
        # Check that the mono motor is moved to the correct positions
        scan_list = list(scan)
        real_energies = [
            i.args[0]
            for i in scan_list
            if i[0] == "set" and i.obj.name == "mono_energy"
        ]
        np.testing.assert_equal(real_energies, expected_energies)
        # Check that the exposure is set correctly
        real_exposures = [
            i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "exposure"
        ]
        np.testing.assert_equal(real_exposures, expected_exposures)

    def test_multi_range(self):
        expected_energies = np.concatenate(
            [
                np.arange(9990, 10001, step=2),
                np.arange(10001, 10011, step=1),
            ]
        )
        expected_exposures = np.asarray([0.5, 1.0])
        scan = xafs_scan(
            -10,
            2,
            0.5,
            0,
            1,
            1.0,
            10,
            E0=self.E0,
            energy_positioners=[self.mono_motor],
            time_positioners=[self.exposure_motor],
        )
        # Check that the mono motor is moved to the correct positions
        scan_list = list(scan)
        real_energies = [
            i.args[0]
            for i in scan_list
            if i[0] == "set" and i.obj.name == "mono_energy"
        ]
        np.testing.assert_equal(real_energies, expected_energies)
        # Check that the exposure is set correctly
        real_exposures = [
            i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "exposure"
        ]
        np.testing.assert_equal(real_exposures, expected_exposures)

    def test_exafs_k_range(self):
        """Ensure that passing in k_min, etc. produces an energy range
        in K-space.

        """
        krange = KRange(E_min=10, k_max=14, k_step=0.5, k_weight=0.5, exposure=0.75)
        expected_energies = krange.energies() + self.E0
        expected_exposures = krange.exposures()
        scan = xafs_scan(
            E_min=10,
            k_step=0.5,
            k_max=14,
            k_exposure=0.75,
            k_weight=0.5,
            E0=self.E0,
            energy_positioners=[self.mono_motor],
            time_positioners=[self.exposure_motor],
        )
        # Check that the mono motor is moved to the correct positions
        scan_list = list(scan)
        real_energies = [
            i.args[0]
            for i in scan_list
            if i[0] == "set" and i.obj.name == "mono_energy"
        ]
        np.testing.assert_equal(real_energies, expected_energies)
        # Check that the exposure is set correctly
        real_exposures = [
            i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "exposure"
        ]
        np.testing.assert_equal(real_exposures, expected_exposures)

    def test_named_E0(self):
        expected_energies = np.concatenate(
            [
                np.arange(8323, 8334, step=2),
                np.arange(8334, 8344, step=1),
            ]
        )
        expected_exposures = np.asarray([0.5, 1.0])
        scan = xafs_scan(
            -10,
            2,
            0.5,
            0,
            1,
            1.0,
            10,
            E0="Ni_K",
            energy_positioners=[self.mono_motor],
            time_positioners=[self.exposure_motor],
        )
        # Check that the mono motor is moved to the correct positions
        scan_list = list(scan)
        real_energies = [
            i.args[0]
            for i in scan_list
            if i[0] == "set" and i.obj.name == "mono_energy"
        ]
        np.testing.assert_equal(real_energies, expected_energies)
        # Check that the exposure is set correctly
        real_exposures = [
            i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "exposure"
        ]
        np.testing.assert_equal(real_exposures, expected_exposures)

    def test_remove_duplicate_energies(self):
        plan = xafs_scan(
            -4, 2, 1.,
            6, 34, 1.,
            40,
            E0=8333,
            energy_positioners=[self.mono_motor],
            time_positioners=[self.exposure_motor],
        )
        msgs = list(plan)
        set_msgs = [m for m in msgs if m.command == 'set' and m.obj.name == "mono_energy"]
        read_msgs = [m for m in msgs if m.command == 'read' and m.obj.name == "I0"]
        energies = [m.args[0] for m in set_msgs]
        # Make sure we only read each point once
        assert len(read_msgs) == len(energies)
