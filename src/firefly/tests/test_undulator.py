import pytest
from bluesky_queueserver_api import BPlan
from qtpy import QtCore

from firefly.devices.undulator import UndulatorDisplay


@pytest.fixture()
def display(qtbot, undulator):
    display = UndulatorDisplay(macros={"DEVICE": undulator.name})
    qtbot.addWidget(display)
    return display


def test_title(display, undulator):
    assert display.windowTitle() == "Undulator"
