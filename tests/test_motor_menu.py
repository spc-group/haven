import pytest
import logging

from haven.instrument import motor, registry
from qtpy import QtWidgets

from firefly.main_window import FireflyMainWindow
from firefly.application import FireflyApplication


@pytest.fixture()
def haven_motors(ioc_motor):
    # Save components to restore later
    components = registry.components
    components.clear()
    # Set up motors
    motor.load_ioc_motors(prefix="vme_crate_ioc", num_motors=3)
    yield registry
    # Restore components
    registry.components = components


def test_motor_menu(haven_motors, qtbot, ffapp):
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    # Create the window
    window = FireflyMainWindow()
    # Check that the menu items have been created
    assert hasattr(window.ui, "menuPositioners")
    assert len(ffapp.motor_actions) == 3


def test_open_motor_window(haven_motors, ffapp):
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    window = FireflyMainWindow()
    # Simulate clicking on the menu action
    action = ffapp.motor_actions[0]
    action.trigger()
    # See if the window was created
    motor_1_name = "FireflyMainWindow_motor_SLT_H_Inb"
    assert motor_1_name in ffapp.windows.keys()
    # assert app.windows[motor_1_name].macros["PREFIX"] == ":m1"
