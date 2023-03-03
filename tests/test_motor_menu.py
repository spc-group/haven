import time
import pytest
import logging

import epics
from haven.instrument import motor, registry
from qtpy import QtWidgets

from firefly.main_window import FireflyMainWindow
from firefly.application import FireflyApplication


def test_motor_menu(ioc_motor, sim_registry, qtbot, ffapp):
    prefix = "vme_crate_ioc"
    motor.load_ioc_motors(prefix=prefix, num_motors=3)
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    # Create the window
    window = FireflyMainWindow()
    # Check that the menu items have been created
    assert hasattr(window.ui, "menuPositioners")
    assert len(ffapp.motor_actions) == 3


def test_open_motor_window(sim_registry, ioc_motor, ffapp):
    # Set up motors in epics
    prefix = "vme_crate_ioc"
    motor_name = "SLT_H_Inb"
    epics.caput(f"{prefix}:m1.DESC", motor_name, wait=True)
    motor.load_ioc_motors(prefix=prefix, num_motors=3)
    for m in sim_registry.findall(label="motors"):
        m.wait_for_connection()
    # Set up the application
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    # Simulate clicking on the menu action (they're in alpha order)
    window = FireflyMainWindow()
    action = ffapp.motor_actions[2]
    action.trigger()
    # See if the window was created
    motor_1_name = "FireflyMainWindow_motor_SLT_H_Inb"
    assert motor_1_name in ffapp.windows.keys()
    # assert ffapp.windows[motor_1_name].macros["PREFIX"] == ":m1"
    # Clean up
    window.close()
