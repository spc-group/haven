from unittest.mock import MagicMock

import pytest
from bluesky_queueserver_api.zmq.aio import REManagerAPI
from ophyd import Device
from ophyd.sim import make_fake_device
from ophydregistry import Registry

import firefly
from firefly.action import WindowAction
from firefly.controller import FireflyController
from firefly.kafka_client import KafkaClient
from firefly.queue_client import QueueClient


@pytest.fixture()
async def controller(qapp):
    controller = FireflyController()
    await controller.setup_instrument(load_instrument=False)
    yield controller


@pytest.fixture()
async def api():
    _api = REManagerAPI()
    return _api


def test_prepare_queue_client(controller, api):
    controller.prepare_queue_client(api=api)
    assert isinstance(controller._queue_client, QueueClient)


def test_queue_actions_enabled(controller, qtbot):
    """Check that the queue control bottons only allow sensible actions.

    For example, if the queue is idle, the "abort" button should be
    disabled, among many others.

    """
    actions = controller.actions.queue_controls
    # Pretend the queue has some things in it
    with qtbot.waitSignal(controller.queue_re_state_changed, timeout=1000):
        controller.queue_re_state_changed.emit("idle")
    # Check the enabled state of all the buttons
    assert actions["start"].isEnabled()
    assert not actions["pause"].isEnabled()
    assert not actions["pause_now"].isEnabled()
    assert not actions["stop_runengine"].isEnabled()
    assert not actions["resume"].isEnabled()
    assert not actions["abort"].isEnabled()
    assert not actions["stop_queue"].isEnabled()
    assert not actions["halt"].isEnabled()
    # Pretend the queue has been paused
    with qtbot.waitSignal(controller.queue_re_state_changed, timeout=1000):
        controller.queue_re_state_changed.emit("paused")
    # Check the enabled state of all the buttons
    assert not actions["start"].isEnabled()
    assert not actions["pause"].isEnabled()
    assert not actions["pause_now"].isEnabled()
    assert not actions["stop_queue"].isEnabled()
    assert actions["stop_runengine"].isEnabled()
    assert actions["resume"].isEnabled()
    assert actions["abort"].isEnabled()
    assert actions["halt"].isEnabled()
    # Pretend the queue is running
    with qtbot.waitSignal(controller.queue_re_state_changed, timeout=1000):
        controller.queue_re_state_changed.emit("running")
    # Check the enabled state of all the buttons
    assert not actions["start"].isEnabled()
    assert actions["pause"].isEnabled()
    assert actions["pause_now"].isEnabled()
    assert not actions["stop_runengine"].isEnabled()
    assert actions["stop_queue"].isEnabled()
    assert not actions["resume"].isEnabled()
    assert not actions["abort"].isEnabled()
    assert not actions["halt"].isEnabled()
    # Pretend the queue is in an unknown state (maybe the environment is closed)
    with qtbot.waitSignal(controller.queue_re_state_changed, timeout=1000):
        controller.queue_re_state_changed.emit(None)


def test_prepare_kafka_client(controller):
    api = MagicMock()
    controller.prepare_kafka_client()
    assert isinstance(controller._kafka_client, KafkaClient)


@pytest.fixture()
def tardis(sim_registry):
    Tardis = make_fake_device(Device)
    tardis = Tardis(name="my_tardis", labels={"tardis"})
    sim_registry.register(tardis)
    return tardis


def test_prepare_generic_device_windows(controller, tardis, mocker):
    """Check for preparing devices with the ``show_device_window`` slot."""
    # mocker.patch.object(controller, "show_device_window", autospec=True)
    actions = controller.device_actions(device_label="tardis", display_file="tardis.ui")
    # Check that actions were created
    assert "my_tardis" in actions.keys()
    assert isinstance(actions["my_tardis"], WindowAction)


@pytest.mark.asyncio
async def test_load_instrument_registry(controller, qtbot, monkeypatch):
    """Check that the instrument registry gets created."""
    assert isinstance(controller.registry, Registry)
    # Mock the underlying haven instrument loader
    loader = MagicMock()
    monkeypatch.setattr(firefly.controller.beamline, "load", loader)
    monkeypatch.setattr(controller, "prepare_queue_client", MagicMock())
    # Reload the devices and see if the registry is changed
    with qtbot.waitSignal(controller.registry_changed):
        await controller.setup_instrument(load_instrument=True)
    # Make sure we loaded the instrument
    assert loader.called


###########################################################
# Tests for connecting the queue client and the controller
###########################################################


def test_queue_stopped(controller):
    """Does the action respond to changes in the queue stopped pending?"""
    client = controller.prepare_queue_client(api=MagicMock())
    assert not controller.actions.queue_controls["stop_queue"].isChecked()
    client.queue_stop_changed.emit(True)
    assert controller.actions.queue_controls["stop_queue"].isChecked()
    client.queue_stop_changed.emit(False)
    assert not controller.actions.queue_controls["stop_queue"].isChecked()


async def test_autostart_changed(controller, qtbot, api):
    """Does the action respond to changes in the queue autostart
    status?

    """
    client = controller.prepare_queue_client(api=api)
    autostart_action = controller.actions.queue_settings["autostart"]
    autostart_action.setChecked(True)
    assert autostart_action.isChecked()
    with qtbot.waitSignal(client.autostart_changed, timeout=3):
        client.autostart_changed.emit(False)
    assert not autostart_action.isChecked()
    with qtbot.waitSignal(client.autostart_changed, timeout=3):
        client.autostart_changed.emit(True)
    assert autostart_action.isChecked()


@pytest.mark.asyncio
async def test_ion_chamber_details_window(qtbot, sim_registry, ion_chamber, controller):
    """Check that the controller opens ion chamber windows from voltmeters
    display.

    """
    vm_action = controller.actions.voltmeter
    ic_action = controller.actions.ion_chambers[ion_chamber.name]
    # Create the ion chamber display
    vm_action = controller.actions.voltmeter
    with qtbot.waitSignal(vm_action.window_shown, timeout=1):
        vm_action.trigger()
    vm_display = vm_action.window.display_widget()
    qtbot.addWidget(vm_display)
    await vm_display.update_devices(sim_registry)
    # Click the ion chamber button
    details_button = vm_display._ion_chamber_rows[0].details_button
    with qtbot.waitSignal(ic_action.window_shown, timeout=1000):
        details_button.click()


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
