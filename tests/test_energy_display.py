import time

from unittest import mock
import pytest
from qtpy import QtWidgets

import haven

from firefly.main_window import FireflyMainWindow
from firefly.energy import EnergyDisplay


def test_energy_macros(qtbot):
    # Create fake device
    mono = haven.instrument.monochromator.Monochromator("mono_ioc", name="monochromator")
    haven.registry.register(
        haven.instrument.energy_positioner.EnergyPositioner(mono_pv="",
                                                            id_prefix="ID25ds",
                                                            name="energy"))
    # from pprint import pprint
    # pprint(dir(mono.energy.user_setpoint))
    # Load display
    FireflyMainWindow()
    display = EnergyDisplay()
    # Check macros
    macros = display.macros()
    assert macros["MONO_MODE_PV"] == "mono_ioc:mode"
    assert macros["MONO_ENERGY_PV"] == "mono_ioc:Energy.RBV"
    assert macros["ID_ENERGY_PV"] == "ID25ds:Energy.VAL"
    assert macros["ID_GAP_PV"] == "ID25ds:Gap.VAL"
