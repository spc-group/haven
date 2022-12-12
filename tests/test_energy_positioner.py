import time

import epics

from haven.instrument.energy_positioner import EnergyPositioner


def test_pseudo_to_real_positioner(ioc_mono, ioc_undulator):
    positioner = EnergyPositioner(
        name="energy", mono_pv="mono_ioc:Energy", id_prefix="id_ioc"
    )
    positioner.mono_energy.wait_for_connection()
    positioner.energy.set(10000)
    assert positioner.get(use_monitor=False).mono_energy.user_setpoint == 10000
    # Move the energy positioner
    positioner.energy.set(5000)
    time.sleep(0.1)  # Caproto breaks pseudopositioner status
    # Check that the mono and ID are both moved
    assert positioner.get(use_monitor=False).mono_energy.user_setpoint == 5000
    assert positioner.get(use_monitor=False).id_energy.setpoint == 5.155


def test_real_to_pseudo_positioner(ioc_mono, ioc_undulator):
    positioner = EnergyPositioner(
        name="energy", mono_pv="mono_ioc:Energy", id_prefix="id_ioc"
    )
    positioner.wait_for_connection(timeout=10.0)
    # Move the mono energy positioner
    epics.caput("mono_ioc:Energy", 5000.0)
    time.sleep(0.1)  # Caproto breaks pseudopositioner status
    assert epics.caget("mono_ioc:Energy.VAL") == 5000.0
    assert epics.caget("mono_ioc:Energy.RBV") == 5000.0
    # Check that the pseudo single is updated
    assert positioner.energy.get(use_monitor=False).readback == 5000.0
