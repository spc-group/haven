from unittest.mock import MagicMock

import pytest
from ophyd import Device
from ophyd.sim import make_fake_device


def test_setup(ffapp):
    api = MagicMock()
    try:
        ffapp.prepare_queue_client(api=api)
    finally:
        ffapp._queue_thread.quit()
        ffapp._queue_thread.wait(msecs=5000)


def test_setup2(ffapp):
    """Verify that multiple tests can use the app without crashing."""
    api = MagicMock()
    try:
        ffapp.prepare_queue_client(api=api)
    finally:
        ffapp._queue_thread.quit()
        ffapp._queue_thread.wait(msecs=5000)


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


@pytest.mark.xfail
def test_prepare_queue_client(ffapp):
    assert False, "Write tests for prepare_queue_client."


@pytest.fixture()
def tardis(sim_registry):
    Tardis = make_fake_device(Device)
    tardis = Tardis(name="my_tardis", labels={"tardis"})
    sim_registry.register(tardis)
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
