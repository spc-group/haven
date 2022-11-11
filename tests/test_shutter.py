from haven.instrument.shutter import load_shutters
from haven import registry


def test_shutter():
    load_shutters()
    shutters = registry.findall(label="shutters")
    assert len(shutters) == 1
    shutterA = shutters[0]
    assert shutterA.name == "Shutter A"
    assert shutterA.open_signal.pvname == "PSS:99ID:FES_OPEN_EPICS.VAL"
