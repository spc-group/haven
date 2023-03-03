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
from firefly.main_window import FireflyMainWindow


def test_setup(ffapp):
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    api = MagicMock()
    FireflyMainWindow()
    ffapp.prepare_queue_client(api=api)


def test_setup2(ffapp):
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    api = MagicMock()
    FireflyMainWindow()
    ffapp.prepare_queue_client(api=api)
