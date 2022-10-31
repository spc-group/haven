import time

import pytest
import epics

from haven import Monochromator
from test_simulated_ioc import ioc_mono


def test_mono_energy_signal(ioc_mono):
    mono = Monochromator("mono_ioc",
                         energy_prefix="mono_ioc",
                         name="monochromator")
    time.sleep(0.1)
    mono.wait_for_connection(timeout=20)
    # Change mono energy
    mono.energy.set(5000)
    time.sleep(1.)
    # Check new value on the IOC
    assert epics.caget("mono_ioc:Energy") == 5000
