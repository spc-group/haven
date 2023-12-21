from unittest import mock
import pytest
from qtpy.QtCore import Qt
from ophyd import sim
from pprint import pprint

from firefly.component_selector import ComponentSelector, ComponentTreeModel, ComponentComboBoxModel


@pytest.fixture()
def motor_registry(ffapp):
    """A simulated motor registry. Like the ophyd-registry but connected to the queueserver."""
    registry = mock.MagicMock()
    registry.root_devices.return_value = [sim.motor1, sim.motor2, sim.motor3]
    return registry

def test_selector_adds_devices(ffapp, motor_registry):
    """Check that the combobox editable options are set based on the allowed detectors."""
    selector = ComponentSelector()
    # Add some items to the
    selector.update_devices(motor_registry)
    # Check that devices were added to the combobox model
    assert selector.combo_box.itemText(0) == "motor1"
    assert selector.combo_box.itemText(1) == "motor1.readback"
    assert selector.combo_box.itemText(2) == "motor1.setpoint"
    # Check that devices were added to the tree model
    tree_model = selector.tree_model
    assert tree_model.item(0).text() == "motor1"

def test_tree_model_adds_devices(ffapp, motor_registry):
    model = ComponentTreeModel()
    model.update_devices(motor_registry)
    # Check "Component" column
    assert model.item(0).text() == "motor1"
    assert model.item(0).child(0, column=0).text() == "readback"
    # Check "Type" column
    assert model.item(0, column=1).text() == "SynAxis"
    assert model.item(0).child(0, column=1).text() == "_ReadbackSignal"


def test_combo_box_model_adds_devices(ffapp, motor_registry):
    model = ComponentComboBoxModel()
    model.update_devices(motor_registry)
    # Check that dot-notation is included
    assert model.item(0).text() == "motor1"
    assert model.item(1).text() == "motor1.readback"


def test_tree_changes_combobox(ffapp, motor_registry, qtbot):
    """Check that the combobox and tree will update each other."""
    selector = ComponentSelector()
    # Add some items to the
    selector.update_devices(motor_registry)
    # Select a tree item
    item = selector.tree_model.item(0).child(1, column=0)
    with qtbot.waitSignal(selector.combo_box.currentTextChanged, timeout=1):
        selector.tree_view.selectionModel().currentChanged.emit(item.index(), item.index())
    assert selector.combo_box.currentText() == "motor1.setpoint"


def test_combobox_changes_tree(ffapp, motor_registry, qtbot):
    """Check that the combobox and tree will update each other."""
    selector = ComponentSelector()
    selector.update_devices(motor_registry)
    # Select a combobox item
    item = selector.tree_model.item(0).child(1, column=0)
    with qtbot.waitSignal(selector.tree_view.selectionModel().currentChanged, timeout=1):
        selector.combo_box.setCurrentIndex(3)
    # assert selector.combo_box.currentText() == "motor1.setpoint"


def test_model_component_from_index(ffapp, motor_registry):
    model = ComponentTreeModel()
    model.update_devices(motor_registry)
    # Can we retrieve a root device based on its name item
    item = model.item(0)
    cpt = model.component_from_index(item.index())
    assert cpt.dotted_name == "motor1"
    # Can we retrieve a component based on its name item
    item = model.item(1).child(1, column=0)
    cpt = model.component_from_index(item.index())
    assert cpt.dotted_name == "motor2.setpoint"
    # Can we retrieve a component based on its type item
    item = model.item(1).child(1, column=1)
    cpt = model.component_from_index(item.index())
    assert cpt.dotted_name == "motor2.setpoint"


def test_model_component_from_dotted_index(ffapp, motor_registry):
    model = ComponentTreeModel()
    model.update_devices(motor_registry)
    # Can we retrieve a root device based on its dotted name
    item = model.item(0)
    cpt = model.component_from_dotted_name("motor1")
    assert cpt.component_item is item
    # Can we retrieve a component based on its dotted name
    item = model.item(1).child(1, column=0)
    cpt = model.component_from_dotted_name("motor2.setpoint")
    assert cpt.component_item is item
