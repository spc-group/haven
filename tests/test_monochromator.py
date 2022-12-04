import time

import epics

from haven import Monochromator


def test_mono_energy_signal(ioc_mono):
    mono = Monochromator("mono_ioc", energy_prefix="mono_ioc", name="monochromator")
    time.sleep(0.1)
    # Change mono energy
    mono.energy.set(5000)
    # Check new value on the IOC
    assert epics.caget("mono_ioc:Energy", use_monitor=False) == 5000
