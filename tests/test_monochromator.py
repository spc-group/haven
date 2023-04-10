import time

import epics

from haven import Monochromator


def test_mono_energy_signal(ioc_mono):
    mono = Monochromator(ioc_mono.prefix.strip(":"), name="monochromator")
    mono.wait_for_connection()
    time.sleep(0.1)
    # Change mono energy
    mono.energy.set(5000)
    # Check new value on the IOC
    assert epics.caget(ioc_mono.pvs["energy"], use_monitor=False) == 5000
