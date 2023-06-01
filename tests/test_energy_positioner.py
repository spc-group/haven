import time

import epics

from haven.instrument.energy_positioner import EnergyPositioner


def test_pseudo_to_real_positioner(ioc_mono, ioc_undulator):
    positioner = EnergyPositioner(
        name="energy",
        mono_pv=ioc_mono.pvs["energy"],
        id_prefix=ioc_undulator.prefix.strip(":"),
        id_tracking_pv=ioc_mono.pvs["id_tracking"],
        id_offset_pv=ioc_mono.pvs["id_offset"],
    )
    positioner.mono_energy.wait_for_connection()
    positioner.id_energy.wait_for_connection()
    positioner.energy.set(10000, timeout=5.0)
    assert positioner.get(use_monitor=False).mono_energy.user_setpoint == 10000
    positioner.id_offset.set(230)
    time.sleep(0.1)
    # Move the energy positioner
    positioner.energy.set(5000)
    time.sleep(0.1)  # Caproto breaks pseudopositioner status
    # Check that the mono and ID are both moved
    assert positioner.get(use_monitor=False).mono_energy.user_setpoint == 5000
    expected_id_energy = 5.0 + positioner.id_offset.get(use_monitor=False) / 1000
    assert positioner.get(use_monitor=False).id_energy.setpoint == expected_id_energy


def test_real_to_pseudo_positioner(ioc_mono, ioc_undulator):
    positioner = EnergyPositioner(
        name="energy",
        mono_pv=ioc_mono.pvs["energy"],
        id_prefix=ioc_undulator.prefix.strip(":"),
        id_tracking_pv=ioc_mono.pvs["id_tracking"],
        id_offset_pv=ioc_mono.pvs["id_offset"],
    )
    positioner.wait_for_connection(timeout=10.0)
    # Move the mono energy positioner
    epics.caput(ioc_mono.pvs["energy"], 5000.0)
    time.sleep(0.1)  # Caproto breaks pseudopositioner status
    assert epics.caget(ioc_mono.pvs["energy"], use_monitor=False) == 5000.0
    # assert epics.caget("mono_ioc:Energy.RBV") == 5000.0
    # Check that the pseudo single is updated
    assert positioner.energy.get(use_monitor=False).readback == 5000.0
