import pytest
import epics

from haven.instrument.energy_positioner import energy_positioner

from simulated_ioc import ioc_mono, ioc_undulator


def test_mono_and_id_positioner(ioc_mono, ioc_undulator):
    assert energy_positioner.get().mono_energy.user_setpoint == 10000
    # Move the energy positioner
    energy_positioner.energy.set(5000).wait(timeout=1)
    # Check that the mono and ID are both moved
    assert epics.caget("mono_ioc:Energy") == 5000
