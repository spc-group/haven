import pytest
from qtpy import QtWidgets

from firefly.main_window import FireflyMainWindow
from firefly.application import FireflyApplication


@pytest.fixture
def app():
    return FireflyApplication()


def test_gain_button(app):
    window = FireflyMainWindow()
    button = window.ui.btnGainUp  # <- what goes here?
    assert type(button) is QtWidgets.QPushButton
    assert hasattr(button, 'clicked')
