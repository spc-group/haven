import time

import pytest
from ophyd.sim import instantiate_fake_device

from haven.instrument.energy_positioner import EnergyPositioner


@pytest.fixture()
def positioner():
    positioner = instantiate_fake_device(
        EnergyPositioner,
        name="energy",
        mono_pv="255idMono",
        id_prefix="255idID",
        id_tracking_pv="255idMono:Tracking",
        id_offset_pv="255idMono:Offset",
    )
    positioner.mono_energy.user_setpoint._use_limits = False
    return positioner


def test_pseudo_to_real_positioner(positioner):
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


def test_real_to_pseudo_positioner(positioner):
    positioner.mono_energy.user_readback.sim_put(5000.0)
    # Move the mono energy positioner
    # epics.caput(ioc_mono.pvs["energy"], 5000.0)
    # time.sleep(0.1)  # Caproto breaks pseudopositioner status
    # assert epics.caget(ioc_mono.pvs["energy"], use_monitor=False) == 5000.0
    # assert epics.caget("mono_ioc:Energy.RBV") == 5000.0
    # Check that the pseudo single is updated
    assert positioner.energy.get(use_monitor=False).readback == 5000.0
