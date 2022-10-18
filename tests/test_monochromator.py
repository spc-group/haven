import pytest
import epics

from haven.instrument.monochromator import monochromator
from simulated_ioc import ioc_mono


def test_mono_energy_signal(ioc_mono):
    monochromator.energy.set(5000).wait()
    assert epics.caget("mono_ioc:Energy") == 5000
