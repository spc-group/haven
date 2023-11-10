import time
import pytest
from unittest.mock import MagicMock
import asyncio

from bluesky import RunEngine, plans as bp
from qtpy.QtCore import QThread
from qtpy.QtTest import QSignalSpy
from bluesky_queueserver_api.zmq import REManagerAPI

from firefly.queue_client import QueueClient
from firefly.application import REManagerAPI


def test_setup(ffapp):
    api = MagicMock()
    ffapp.prepare_queue_client(api=api)


def test_setup2(ffapp):
    """Verify that multiple tests can use the app without crashing."""
    api = MagicMock()
    ffapp.prepare_queue_client(api=api)


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
