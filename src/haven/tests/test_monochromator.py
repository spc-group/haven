import time

import epics

from haven import Monochromator


def test_mono_energy_signal():
    mono = Monochromator("255idMono", name="monochromator")
    # Check PVs are correct
    mono.energy.user_readback.pvname == "255idMono:Energy.RBV"
