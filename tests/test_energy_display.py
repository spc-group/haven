import time
from unittest import mock

import pytest
from qtpy import QtWidgets, QtCore
from bluesky_queueserver_api import BPlan
import haven
from haven.instrument.monochromator import load_monochromator
from haven.instrument.energy_positioner import load_energy_positioner

from firefly.main_window import FireflyMainWindow
from firefly.energy import EnergyDisplay


def test_energy_macros(qtbot, ffapp, sim_registry):
    # Create fake device
    mono = haven.instrument.monochromator.Monochromator("mono_ioc", name="monochromator")
    sim_registry.register(
        haven.instrument.energy_positioner.EnergyPositioner(mono_pv="mono_ioc:Energy",
                                                            id_offset_pv="mono_ioc:ID_offset",
                                                            id_prefix="id_ioc",
                                                            name="energy"))
    # Load display
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    FireflyMainWindow()
    display = EnergyDisplay()
    # Check macros
    macros = display.macros()
    assert macros["MONO_MODE_PV"] == "mono_ioc:mode"
    assert macros["MONO_ENERGY_PV"] == "mono_ioc:Energy.RBV"
    assert macros["ID_ENERGY_PV"] == "id_ioc:Energy.VAL"
    assert macros["ID_GAP_PV"] == "id_ioc:Gap.VAL"


def test_move_energy(qtbot, ffapp, sim_registry):
    mono = haven.instrument.monochromator.Monochromator("mono_ioc", name="monochromator")
    sim_registry.register(
        haven.instrument.energy_positioner.EnergyPositioner(mono_pv="mono_ioc:Energy",
                                                            id_offset_pv="mono_ioc:ID_offset",
                                                            id_prefix="id_ioc",
                                                            name="energy"))
    # Load display
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    FireflyMainWindow()
    disp = EnergyDisplay()
    # Click the set energy button
    btn = disp.ui.set_energy_button
    expected_item = BPlan('set_energy', energy=8402.0)
    def check_item(item):
        return item.to_dict() == expected_item.to_dict()
    qtbot.keyClicks(disp.target_energy_lineedit, '8402')
    with qtbot.waitSignal(ffapp.queue_item_added, timeout=1000,
                          check_params_cb=check_item):
        qtbot.mouseClick(btn, QtCore.Qt.LeftButton)


def test_predefined_energies(qtbot, ffapp, ioc_mono, sim_registry):
    load_monochromator(config={
        "monochromator": {
            "ioc": "mono_ioc",
        },
    })
    load_energy_positioner()
    # Create fake device
    mono = haven.instrument.monochromator.Monochromator("mono_ioc", name="monochromator")
    sim_registry.register(
        haven.instrument.energy_positioner.EnergyPositioner(mono_pv="mono_ioc:Energy",
                                                            id_offset_pv="mono_ioc:ID_offset",
                                                            id_prefix="id_ioc",
                                                            name="energy"))
    # Set up the required Application state
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    # Load display
    FireflyMainWindow()
    disp = EnergyDisplay()
    # Check that the combo box was populated
    combo_box = disp.ui.edge_combo_box
    assert combo_box.count() > 0
    assert combo_box.itemText(0) == "Select edge…"
    assert combo_box.itemText(1) == "Ca K (4038 eV)"
    # Does it filter energies outside the usable range?
    assert combo_box.count() < 250
    # Does it update the energy line edit?
    with qtbot.waitSignal(combo_box.activated, timeout=1000):
        qtbot.keyClicks(combo_box, "Ni K (8333 eV)\t")
        combo_box.activated.emit(9)  # <- this shouldn't be necessary
    line_edit = disp.ui.target_energy_lineedit
    assert line_edit.text() == "8333.000"
