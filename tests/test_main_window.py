import pytest

from firefly.main_window import FireflyMainWindow
from firefly.application import FireflyApplication


@pytest.fixture
def app():
    yield FireflyApplication()


def test_add_menu_action(app):
    window = FireflyMainWindow()
    # Check that it's not set up with the right menu yet
    assert not hasattr(window, "actionMake_Salad")
    # Add a menu item
    action = window.add_menu_action(action_name="actionMake_Salad",
                                    text="Make Salad", menu=window.ui.menuTools)
    assert hasattr(window.ui, "actionMake_Salad")
    assert hasattr(window, "actionMake_Salad")    
    assert action.text() == "Make Salad"
    assert action.objectName() == "actionMake_Salad"


def test_customize_ui(app):
    window = FireflyMainWindow()
    assert hasattr(window.ui, "menuScans")
