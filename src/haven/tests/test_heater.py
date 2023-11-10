import time

from epics import caget, caput
from haven.instrument.heater import CapillaryHeater, load_heaters


PREFIX = "255idptc10:"


def test_load_heaters():
    heaters = load_heaters()
    assert len(heaters) == 1
    heater = heaters[0]
    assert heaters[0].name == "capillary_heater"
