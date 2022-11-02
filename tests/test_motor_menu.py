import pytest
import logging

from haven.instrument import motor, registry
from qtpy import QtWidgets

from firefly.main_window import FireflyMainWindow
from firefly.application import FireflyApplication
from test_simulated_ioc import ioc_motor


@pytest.fixture()
def haven_motors():
    # Save components to restore later
    components = registry.components
    components.clear()
    # Set up motors
    motor.load_vme_motors()
    yield registry
    # Restore components
    registry.components = components


def test_motor_menu(ioc_motor, qtbot):
    app = QtWidgets.QApplication.instance()
    # Load motors
    motor.load_vme_motors()
    # Create the window
    window = FireflyMainWindow()
    # Check that the menu items have been created
    assert hasattr(window.ui, "menuPositioners")
    assert len(app.motor_actions) == 3


def test_open_motor_window(ioc_motor, haven_motors):
    app = FireflyApplication()
    window = FireflyMainWindow()
    # Simulate clicking on the menu action
    action = app.motor_actions[0]
    action.trigger()
    # See if the window was created
    motor_1_name = "FireflyMainWindow_motor_SLT_H_Inb"
    assert motor_1_name in app.windows.keys()
    # assert app.windows[motor_1_name].macros["PREFIX"] == ":m1"
