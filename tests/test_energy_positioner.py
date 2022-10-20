import time

import pytest
import epics

from haven.instrument.energy_positioner import EnergyPositioner

from test_simulated_ioc import ioc_mono, ioc_undulator


def test_pseudo_to_real_positioner(ioc_mono, ioc_undulator):
    positioner = EnergyPositioner(
        name="energy", mono_energy_pv="mono_ioc:Energy", id_prefix="id_ioc"
    )
    print(positioner.mono_energy, positioner.id_energy)
    positioner.wait_for_connection()
    assert positioner.get().mono_energy.user_setpoint == 10000
    # Move the energy positioner
    positioner.energy.set(5000)
    time.sleep(0.1)  # Caproto breaks pseudopositioner status
    # Check that the mono and ID are both moved
    assert positioner.get().mono_energy.user_setpoint == 5000
    assert positioner.get().id_energy.setpoint == 5100


def test_real_to_pseudo_positioner(ioc_mono, ioc_undulator):
    positioner = EnergyPositioner(
        name="energy", mono_energy_pv="mono_ioc:Energy", id_prefix="id_ioc"
    )
    positioner.wait_for_connection(timeout=10.0)
    # Move the mono energy positioner
    epics.caput("mono_ioc:Energy", 5000.0)
    time.sleep(0.1)  # Caproto breaks pseudopositioner status
    assert epics.caget("mono_ioc:Energy.VAL") == 5000.0
    assert epics.caget("mono_ioc:Energy.RBV") == 5000.0
    # Check that the pseudo single is updated
    assert positioner.energy.get().readback == 5000.0
