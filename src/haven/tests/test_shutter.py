from unittest import mock
from haven.instrument import shutter
from haven import registry


def test_shutter(sim_registry, beamline_connected):
    shutter.load_shutters()
    shutters = list(registry.findall(label="shutters"))
    assert len(shutters) == 2
    shutterA = registry.find(name="front_end_shutter")
    assert shutterA.name == "front_end_shutter"
    assert shutterA.open_signal.pvname == "PSS:99ID:FES_OPEN_EPICS.VAL"
    assert shutterA.close_signal.pvname == "PSS:99ID:FES_CLOSE_EPICS.VAL"
    assert shutterA.pss_state.pvname == "PSS:99ID:A_BEAM_PRESENT"
    shutterC = registry.find(name="hutch_shutter")
    assert shutterC.name == "hutch_shutter"
    assert shutterC.open_signal.pvname == "PSS:99ID:SCS_OPEN_EPICS.VAL"
    assert shutterC.close_signal.pvname == "PSS:99ID:SCS_CLOSE_EPICS.VAL"
    assert shutterC.pss_state.pvname == "PSS:99ID:C_BEAM_PRESENT"
