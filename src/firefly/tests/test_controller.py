from unittest.mock import MagicMock

import pytest
from ophyd import Device
from ophyd.sim import make_fake_device
from ophydregistry import Registry
from haven.instrument import motor
import firefly
from firefly.controller import FireflyController
from firefly.main_window import FireflyMainWindow
from firefly.queue_client import QueueClient


@pytest.fixture()
def controller(qapp):
    controller = FireflyController()
    controller.setup_instrument(load_instrument=False)
    return controller


@pytest.fixture()
def ffapp():
    return MagicMock()


def test_prepare_queue_client(controller):
    api = MagicMock()
    controller.prepare_queue_client(api=api)
    assert isinstance(controller._queue_client, QueueClient)


def test_queue_actions_enabled(controller, qtbot):
    """Check that the queue control bottons only allow sensible actions.

    For example, if the queue is idle, the "abort" button should be
    disabled, among many others.

    """
    # Pretend the queue has some things in it
    with qtbot.waitSignal(controller.queue_re_state_changed):
        controller.queue_re_state_changed.emit("idle")
    # Check the enabled state of all the buttons
    assert controller.start_queue_action.isEnabled()
    assert not controller.stop_runengine_action.isEnabled()
    assert not controller.pause_runengine_action.isEnabled()
    assert not controller.pause_runengine_now_action.isEnabled()
    assert not controller.resume_runengine_action.isEnabled()
    assert not controller.abort_runengine_action.isEnabled()
    assert not controller.halt_runengine_action.isEnabled()
    # Pretend the queue has been paused
    with qtbot.waitSignal(controller.queue_re_state_changed):
        controller.queue_re_state_changed.emit("paused")
    # Check the enabled state of all the buttons
    assert not controller.start_queue_action.isEnabled()
    assert not controller.pause_runengine_action.isEnabled()
    assert not controller.pause_runengine_now_action.isEnabled()
    assert controller.stop_runengine_action.isEnabled()
    assert controller.resume_runengine_action.isEnabled()
    assert controller.abort_runengine_action.isEnabled()
    assert controller.halt_runengine_action.isEnabled()
    # Pretend the queue is running
    with qtbot.waitSignal(controller.queue_re_state_changed):
        controller.queue_re_state_changed.emit("running")
    # Check the enabled state of all the buttons
    assert not controller.start_queue_action.isEnabled()
    assert controller.pause_runengine_action.isEnabled()
    assert controller.pause_runengine_now_action.isEnabled()
    assert not controller.stop_runengine_action.isEnabled()
    assert not controller.resume_runengine_action.isEnabled()
    assert not controller.abort_runengine_action.isEnabled()
    assert not controller.halt_runengine_action.isEnabled()
    # Pretend the queue is in an unknown state (maybe the environment is closed)
    with qtbot.waitSignal(controller.queue_re_state_changed):
        controller.queue_re_state_changed.emit(None)


@pytest.fixture()
def tardis(sim_registry):
    Tardis = make_fake_device(Device)
    tardis = Tardis(name="my_tardis", labels={"tardis"})
    return tardis


def test_prepare_generic_device_windows(controller, tardis, mocker):
    """Check for preparing devices with the ``show_device_window`` slot."""
    mocker.patch.object(controller, "show_device_window", autospec=True)
    controller._prepare_device_windows(
        device_label="tardis", attr_name="tardis", ui_file="tardis.ui"
    )
    # Check that actions were created
    assert hasattr(controller, "tardis_actions")
    assert "my_tardis" in controller.tardis_actions
    # Check that slots were set up to open the window
    assert hasattr(controller, "tardis_window_slots")
    assert len(controller.tardis_window_slots) == 1
    # Call the slot and see that the right one was used
    controller.tardis_window_slots[0]()
    controller.show_device_window.assert_called_once_with(
        device=tardis, device_label="tardis", ui_file="tardis.ui", device_key="DEVICE"
    )
    # Check that there's a dictionary to keep track of open windows
    assert hasattr(controller, "tardis_windows")


def test_prepare_device_specific_windows(controller, tardis):
    """Check for preparing devices with device specific
    ``show_<device_class>_window`` slot.

    """
    slot = MagicMock()
    controller._prepare_device_windows(
        device_label="tardis", attr_name="tardis", ui_file="tardis.ui", window_slot=slot
    )
    # Check that actions were created
    assert hasattr(controller, "tardis_actions")
    assert "my_tardis" in controller.tardis_actions
    # Check that slots were set up to open the window
    assert hasattr(controller, "tardis_window_slots")
    assert len(controller.tardis_window_slots) == 1
    # Call the slot and see that the right one was used
    controller.tardis_window_slots[0]()
    slot.assert_called_once_with(
        device=tardis,
    )
    # Check that there's a dictionary to keep track of open windows
    assert hasattr(controller, "tardis_windows")


def test_load_instrument_registry(controller, qtbot, monkeypatch):
    """Check that the instrument registry gets created."""
    assert isinstance(controller.registry, Registry)
    # Mock the underlying haven instrument loader
    loader = MagicMock()
    monkeypatch.setattr(firefly.controller, "load_haven_instrument", loader)
    monkeypatch.setattr(controller, "prepare_queue_client", MagicMock())
    # Reload the devices and see if the registry is changed
    with qtbot.waitSignal(controller.registry_changed):
        controller.setup_instrument(load_instrument=True)
    # Make sure we loaded the instrument
    assert loader.called


def test_open_camera_viewer_actions(controller, qtbot, sim_camera):
    # Now get the cameras ready
    controller._prepare_device_windows(
        device_label="cameras",
        attr_name="camera",
        ui_file="area_detector_viewer.py",
        device_key="AD",
    )
    assert hasattr(controller, "camera_actions")
    assert len(controller.camera_actions) == 1
    # Launch an action and see that a window opens
    list(controller.camera_actions.values())[0].trigger()
    assert "FireflyMainWindow_camera_s255id-gige-A" in controller.windows.keys()


def test_open_area_detector_viewer_actions(controller, qtbot, sim_camera):
    # Get the area detector parts ready
    controller._prepare_device_windows(
        device_label="area_detectors",
        attr_name="area_detector",
        ui_file="area_detector_viewer.py",
        device_key="AD",
    )
    assert hasattr(controller, "area_detector_actions")
    assert len(controller.area_detector_actions) == 1
    # Launch an action and see that a window opens
    list(controller.area_detector_actions.values())[0].trigger()
    assert "FireflyMainWindow_area_detector_s255id-gige-A" in controller.windows.keys()


############
# From old src/firefly/tests/test_motor_menu.py
    

@pytest.fixture
def fake_motors(sim_registry):
    motor_names = ["motorA", "motorB", "motorC"]
    motors = []
    for name in motor_names:
        this_motor = make_fake_device(motor.HavenMotor)(
            name=name, labels={"extra_motors"}
        )
        motors.append(this_motor)
    return motors


def test_open_motor_window(fake_motors, controller, qtbot):
    # Simulate clicking on the menu action (they're in alpha order)
    action = controller.motor_actions["motorC"]
    action.trigger()
    # See if the window was created
    motor_3_name = "FireflyMainWindow_motor_motorC"
    assert motor_3_name in controller.windows.keys()
    macros = controller.windows[motor_3_name].display_widget().macros()
    assert macros["MOTOR"] == "motorC"


def test_motor_menu(fake_motors, controller, qtbot):
    # Create the window
    window = FireflyMainWindow()
    qtbot.addWidget(window)
    # Check that the menu items have been created
    assert hasattr(window.ui, "positioners_menu")
    assert len(controller.motor_actions) == 3
    window.destroy()


###########################################################
# Tests for connecting the queue client and the controller
###########################################################

def test_queue_stopped(controller):
    """Does the action respond to changes in the queue stopped pending?"""
    client = controller.prepare_queue_client(api=MagicMock())
    assert not controller.queue_stop_action.isChecked()
    client.queue_stop_changed.emit(True)
    assert controller.queue_stop_action.isChecked()
    client.queue_stop_changed.emit(False)
    assert not controller.queue_stop_action.isChecked()


def test_autostart_changed(controller, qtbot):
    """Does the action respond to changes in the queue autostart
    status?

    """
    client = controller.prepare_queue_client(api=MagicMock())
    controller.queue_autostart_action.setChecked(True)
    assert controller.queue_autostart_action.isChecked()
    with qtbot.waitSignal(client.autostart_changed, timeout=3):
        client.autostart_changed.emit(False)
    assert not controller.queue_autostart_action.isChecked()
    with qtbot.waitSignal(client.autostart_changed, timeout=3):
        client.autostart_changed.emit(True)
    assert controller.queue_autostart_action.isChecked()


################################################################
# Tests for integration of controller with XRF detector display
################################################################

def test_open_xrf_detector_viewer_actions(controller, xspress, qtbot):
    # Get the area detector parts ready
    controller._prepare_device_windows(
        device_label="xrf_detectors",
        attr_name="xrf_detector",
        ui_file="xrf_detector.py",
        device_key="DEV",
    )
    assert hasattr(controller, "xrf_detector_actions")
    assert len(controller.xrf_detector_actions) == 1
    # Launch an action and see that a window opens
    list(controller.xrf_detector_actions.values())[0].trigger()
    qtbot.addWidget(controller.windows["FireflyMainWindow_xrf_detector_vortex_me4"])
    assert "FireflyMainWindow_xrf_detector_vortex_me4" in controller.windows.keys()


#############################################################
# Integration tests for controller with ion chamber displays
#############################################################

def test_open_ion_chamber_window(I0, It, controller):
    # Simulate clicking on the menu action (they're in alpha order)
    action = controller.ion_chamber_actions["It"]
    action.trigger()
    # See if the window was created
    ion_chamber_name = "FireflyMainWindow_ion_chamber_It"
    assert ion_chamber_name in controller.windows.keys()
    macros = controller.windows[ion_chamber_name].display_widget().macros()
    assert macros["IC"] == "It"


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
