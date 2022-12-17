import pytest

from firefly.main_window import FireflyMainWindow, PlanMainWindow
from firefly.application import FireflyApplication


@pytest.fixture
def app():
    yield FireflyApplication()


def test_navbar(app):
    window = PlanMainWindow()
    # Check navbar actions on the app
    assert hasattr(app, 'pause_runengine_action')
    # Check that the navbar actions are set up properly
    assert hasattr(window.ui, "navbar")
    navbar = window.ui.navbar
    # Navigation actions are removed
    assert window.ui.actionHome not in navbar.actions()
    # Run engine actions have been added to the navbar
    assert app.pause_runengine_action in navbar.actions()

def test_navbar_autohide(qapp, qtbot):
    """Test that the queue navbar is only visible when plans are queued."""
    window = PlanMainWindow()
    window.show()
    navbar = window.ui.navbar
    assert navbar.isVisible()
    # Make the queue be empty
    qapp.queue_length_changed.emit(0)
    assert not navbar.isVisible()


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
