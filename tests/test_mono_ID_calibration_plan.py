from unittest.mock import MagicMock
import pytest
from ophyd import sim
from bluesky.callbacks.best_effort import BestEffortCallback
from lmfit.models import QuadraticModel

from haven import mono_ID_calibration
from run_engine import RunEngineStub


@pytest.fixture()
def mono_motor(sim_registry):
    motor = sim_registry.register(
        sim.SynAxis(name="energy_mono_energy", labels={"motors", "energies"})
    )
    yield motor


@pytest.fixture()
def pitch2_motor(sim_registry):
    motor = sim_registry.register(
        sim.SynAxis(name="monochromator_pitch2", labels={"motors"})
    )
    yield motor    


@pytest.fixture()
def id_motor(sim_registry):
    motor = sim_registry.register(
        sim.SynAxis(name="energy_id_energy", labels={"motors", "energies"})
    )
    yield motor


@pytest.fixture()
def ion_chamber(sim_registry, id_motor):
    I0 = sim_registry.register(
        sim.SynGauss(
            "I0",
            id_motor,
            "energy_id_energy",
            center=8.,
            Imax=1,
            sigma=1,
            labels={"ion_chambers"},
        )
    )
    yield I0


def test_moves_energy(mono_motor, id_motor, ion_chamber, pitch2_motor):
    """Simple test to ensure that the plan moves the mono and undulators
    to the right starting energy."""
    # Execute the plan
    id_motor.set(8)
    fit_model = MagicMock()
    RE = RunEngineStub()
    RE(mono_ID_calibration(energies=[8000], energy_motor=mono_motor, fit_model=fit_model))
    assert mono_motor.readback.get() == 8000.


def test_aligns_pitch(mono_motor, id_motor, ion_chamber, pitch2_motor):
    fit_model = MagicMock()
    plan = mono_ID_calibration(energies=[8000], energy_motor=mono_motor, fit_model=fit_model)
    messages = list(plan)
    device_names = [getattr(m.obj, 'name', None) for m in messages]
    assert "monochromator_pitch2" in device_names


def test_aligns_mono_energy(mono_motor, id_motor, ion_chamber, pitch2_motor):
    fit_model = MagicMock()
    plan = mono_ID_calibration(energies=[8000], energy_motor=mono_motor, fit_model=fit_model)
    messages = list(plan)
    id_messages = [m for m in messages if getattr(m.obj, 'name', '') == "energy_id_energy"]
    # Check that messages were produced for each point in the mono scan
    npts = 40  # Taken from `align_motor` plan
    assert len(id_messages) >= npts
    

def test_fitting_callback(mono_motor, id_motor, ion_chamber, pitch2_motor):
    fit_model = MagicMock()
    plan = mono_ID_calibration(energies=[8000, 9000], energy_motor=mono_motor, fit_model=fit_model)
    # Execute the plan in the runengine
    RE = RunEngineStub()
    result = RE(plan)
    # Check that the fitting results are available
    fit_model.fit.assert_called_once()
    # assert False
