from unittest.mock import MagicMock

import pytest
from ophyd import Device
from ophyd.sim import make_fake_device
from ophydregistry import Registry

import firefly
from firefly.queue_client import QueueClient


def test_prepare_queue_client(ffapp):
    api = MagicMock()
    ffapp.prepare_queue_client(api=api)
    assert isinstance(ffapp._queue_client, QueueClient)


def test_queue_actions_enabled(ffapp, qtbot):
    """Check that the queue control bottons only allow sensible actions.

    For example, if the queue is idle, the "abort" button should be
    disabled, among many others.

    """
    # Pretend the queue has some things in it
    with qtbot.waitSignal(ffapp.queue_re_state_changed):
        ffapp.queue_re_state_changed.emit("idle")
    # Check the enabled state of all the buttons
    assert ffapp.start_queue_action.isEnabled()
    assert not ffapp.stop_runengine_action.isEnabled()
    assert not ffapp.pause_runengine_action.isEnabled()
    assert not ffapp.pause_runengine_now_action.isEnabled()
    assert not ffapp.resume_runengine_action.isEnabled()
    assert not ffapp.abort_runengine_action.isEnabled()
    assert not ffapp.halt_runengine_action.isEnabled()
    # Pretend the queue has been paused
    with qtbot.waitSignal(ffapp.queue_re_state_changed):
        ffapp.queue_re_state_changed.emit("paused")
    # Check the enabled state of all the buttons
    assert not ffapp.start_queue_action.isEnabled()
    assert not ffapp.pause_runengine_action.isEnabled()
    assert not ffapp.pause_runengine_now_action.isEnabled()
    assert ffapp.stop_runengine_action.isEnabled()
    assert ffapp.resume_runengine_action.isEnabled()
    assert ffapp.abort_runengine_action.isEnabled()
    assert ffapp.halt_runengine_action.isEnabled()
    # Pretend the queue is running
    with qtbot.waitSignal(ffapp.queue_re_state_changed):
        ffapp.queue_re_state_changed.emit("running")
    # Check the enabled state of all the buttons
    assert not ffapp.start_queue_action.isEnabled()
    assert ffapp.pause_runengine_action.isEnabled()
    assert ffapp.pause_runengine_now_action.isEnabled()
    assert not ffapp.stop_runengine_action.isEnabled()
    assert not ffapp.resume_runengine_action.isEnabled()
    assert not ffapp.abort_runengine_action.isEnabled()
    assert not ffapp.halt_runengine_action.isEnabled()
    # Pretend the queue is in an unknown state (maybe the environment is closed)
    with qtbot.waitSignal(ffapp.queue_re_state_changed):
        ffapp.queue_re_state_changed.emit(None)


def test_prepare_queue_client(ffapp):
    api = MagicMock()
    ffapp.prepare_queue_client(api=api)
    # Check that a timer was created
    assert isinstance(ffapp._queue_client, QueueClient)


@pytest.fixture()
def tardis(sim_registry):
    Tardis = make_fake_device(Device)
    tardis = Tardis(name="my_tardis", labels={"tardis"})
    return tardis


def test_prepare_generic_device_windows(ffapp, tardis, mocker):
    """Check for preparing devices with the ``show_device_window`` slot."""
    mocker.patch.object(ffapp, "show_device_window", autospec=True)
    ffapp._prepare_device_windows(
        device_label="tardis", attr_name="tardis", ui_file="tardis.ui"
    )
    # Check that actions were created
    assert hasattr(ffapp, "tardis_actions")
    assert "my_tardis" in ffapp.tardis_actions
    # Check that slots were set up to open the window
    assert hasattr(ffapp, "tardis_window_slots")
    assert len(ffapp.tardis_window_slots) == 1
    # Call the slot and see that the right one was used
    ffapp.tardis_window_slots[0]()
    ffapp.show_device_window.assert_called_once_with(
        device=tardis, device_label="tardis", ui_file="tardis.ui", device_key="DEVICE"
    )
    # Check that there's a dictionary to keep track of open windows
    assert hasattr(ffapp, "tardis_windows")


def test_prepare_device_specific_windows(ffapp, tardis):
    """Check for preparing devices with device specific
    ``show_<device_class>_window`` slot.

    """
    slot = MagicMock()
    ffapp._prepare_device_windows(
        device_label="tardis", attr_name="tardis", ui_file="tardis.ui", window_slot=slot
    )
    # Check that actions were created
    assert hasattr(ffapp, "tardis_actions")
    assert "my_tardis" in ffapp.tardis_actions
    # Check that slots were set up to open the window
    assert hasattr(ffapp, "tardis_window_slots")
    assert len(ffapp.tardis_window_slots) == 1
    # Call the slot and see that the right one was used
    ffapp.tardis_window_slots[0]()
    slot.assert_called_once_with(
        device=tardis,
    )
    # Check that there's a dictionary to keep track of open windows
    assert hasattr(ffapp, "tardis_windows")


def test_load_instrument_registry(ffapp, qtbot, monkeypatch):
    """Check that the instrument registry gets created."""
    assert isinstance(ffapp.registry, Registry)
    # Mock the underlying haven instrument loader
    loader = MagicMock()
    monkeypatch.setattr(firefly.application, "load_haven_instrument", loader)
    monkeypatch.setattr(ffapp, "prepare_queue_client", MagicMock())
    # Reload the devices and see if the registry is changed
    with qtbot.waitSignal(ffapp.registry_changed):
        ffapp.setup_instrument(load_instrument=True)
    # Make sure we loaded the instrument
    assert loader.called


def test_open_camera_viewer_actions(ffapp, qtbot, sim_camera):
    # Now get the cameras ready
    ffapp._prepare_device_windows(
        device_label="cameras",
        attr_name="camera",
        ui_file="area_detector_viewer.py",
        device_key="AD",
    )
    assert hasattr(ffapp, "camera_actions")
    assert len(ffapp.camera_actions) == 1
    # Launch an action and see that a window opens
    list(ffapp.camera_actions.values())[0].trigger()
    assert "FireflyMainWindow_camera_s255id-gige-A" in ffapp.windows.keys()


def test_open_area_detector_viewer_actions(ffapp, qtbot, sim_camera):
    # Get the area detector parts ready
    ffapp._prepare_device_windows(
        device_label="area_detectors",
        attr_name="area_detector",
        ui_file="area_detector_viewer.py",
        device_key="AD",
    )
    assert hasattr(ffapp, "area_detector_actions")
    assert len(ffapp.area_detector_actions) == 1
    # Launch an action and see that a window opens
    list(ffapp.area_detector_actions.values())[0].trigger()
    assert "FireflyMainWindow_area_detector_s255id-gige-A" in ffapp.windows.keys()


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


def test_open_motor_window(fake_motors, qapp, qtbot):
    # Simulate clicking on the menu action (they're in alpha order)
    action = ffapp.motor_actions["motorC"]
    action.trigger()
    # See if the window was created
    motor_3_name = "FireflyMainWindow_motor_motorC"
    assert motor_3_name in ffapp.windows.keys()
    macros = ffapp.windows[motor_3_name].display_widget().macros()
    assert macros["MOTOR"] == "motorC"


def test_motor_menu(fake_motors, qapp, qtbot):
    # Create the window
    window = FireflyMainWindow()
    qtbot.addWidget(window)
    # Check that the menu items have been created
    assert hasattr(window.ui, "positioners_menu")
    assert len(ffapp.motor_actions) == 3
    window.destroy()


##########################################
# From src/firefly/tests/test_queue_client.py


def test_queue_stopped(client):
    """Does the action respond to changes in the queue stopped pending?"""
    assert not ffapp.queue_stop_action.isChecked()
    client.queue_stop_changed.emit(True)
    assert ffapp.queue_stop_action.isChecked()
    client.queue_stop_changed.emit(False)
    assert not ffapp.queue_stop_action.isChecked()


def test_autostart_changed(client, qtbot):
    """Does the action respond to changes in the queue autostart
    status?

    """
    ffapp.queue_autostart_action.setChecked(True)
    assert ffapp.queue_autostart_action.isChecked()
    with qtbot.waitSignal(client.autostart_changed, timeout=3):
        client.autostart_changed.emit(False)
    assert not ffapp.queue_autostart_action.isChecked()
    with qtbot.waitSignal(client.autostart_changed, timeout=3):
        client.autostart_changed.emit(True)
    assert ffapp.queue_autostart_action.isChecked()



###############################################################
# From: src/firefly/tests/test_xrf_detector_display.py

def test_open_xrf_detector_viewer_actions(ffapp, qtbot, det_fixture, request):
    sim_det = request.getfixturevalue(det_fixture)
    # Get the area detector parts ready
    ffapp._prepare_device_windows(
        device_label="xrf_detectors",
        attr_name="xrf_detector",
        ui_file="xrf_detector.py",
        device_key="DEV",
    )
    assert hasattr(ffapp, "xrf_detector_actions")
    assert len(ffapp.xrf_detector_actions) == 1
    # Launch an action and see that a window opens
    list(ffapp.xrf_detector_actions.values())[0].trigger()
    assert "FireflyMainWindow_xrf_detector_vortex_me4" in ffapp.windows.keys()


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
