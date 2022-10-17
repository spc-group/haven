import pytest
import logging

from firefly.main_window import FireflyMainWindow
from firefly.application import FireflyApplication
from test_simulated_ioc import ioc_motor


logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def app():
    yield FireflyApplication()



def test_motor_menu(ioc_motor, app):
    from haven.instrument import motor
    window = FireflyMainWindow()
    assert hasattr(window.ui, "menuPositioners")
    # Check that the menu items have been created
    assert len(window.ui.motor_actions) == 3
