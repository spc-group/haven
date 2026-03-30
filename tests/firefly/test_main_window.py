import pytest
from qtpy.QtWidgets import QAction

from firefly.controller import ActionsRegistry
from firefly.main_window import FireflyMainWindow, PlanMainWindow


@pytest.fixture()
def window(qapp, qtbot):
    window = FireflyMainWindow()
    qtbot.addWidget(window)
    return window


@pytest.fixture()
def actions():
    registry = ActionsRegistry()
    return registry


def test_navbar(qapp, qtbot, actions):
    actions.queue_controls = {
        "pause": QAction(),
        "start": QAction(),
    }
    window = PlanMainWindow(actions=actions)
    qtbot.addWidget(window)
    # Check that the navbar actions are set up properly
    assert hasattr(window.ui, "navbar")
    navbar = window.ui.navbar
    # Navigation actions are removed
    assert window.ui.actionHome not in navbar.actions()
    # Run engine actions have been added to the navbar
    assert actions.queue_controls["pause"] in navbar.actions()
    assert actions.queue_controls["start"] in navbar.actions()


def test_navbar_autohide(qtbot, actions):
    """Test that the queue navbar is only visible when plans are queued."""
    window = PlanMainWindow(actions=actions)
    qtbot.addWidget(window)
    window.show()
    navbar = window.ui.navbar
    # Pretend the queue has some things in it
    window.update_queue_controls({"items_in_queue": 5})
    assert navbar.isVisible()
    # Make the queue be empty
    window.update_queue_controls({"items_in_queue": 0})
    assert not navbar.isVisible()


def test_add_menu_action(window):
    # Check that it's not set up with the right menu yet
    assert not hasattr(window, "actionMake_Salad")
    # Add a menu item
    action = window.add_menu_action(
        action_name="actionMake_Salad", text="Make Salad", menu=window.ui.menuTools
    )
    assert hasattr(window.ui, "actionMake_Salad")
    assert hasattr(window, "actionMake_Salad")
    assert action.text() == "Make Salad"
    assert action.objectName() == "actionMake_Salad"


def test_motor_menu(qapp, qtbot, actions):
    actions.motors = {
        "A": QAction(),
        "B": QAction(),
        "C": QAction(),
    }
    window = FireflyMainWindow(actions=actions)
    qtbot.addWidget(window)
    # Check that the menu items have been created
    assert hasattr(window.ui, "positioners_menu")
    assert hasattr(window.ui, "motors_menu")
    assert window.ui.motors_menu.actions() == list(actions.motors.values())


def test_plans_menu(qapp, qtbot, actions):
    actions.plans = {
        "start": QAction(),
        "pause": QAction(),
        "abort": QAction(),
    }
    window = FireflyMainWindow(actions=actions)
    qtbot.addWidget(window)
    assert hasattr(window.ui, "plans_menu")
    window.ui.plans_menu.actions() == actions.plans


def test_show_message(window):
    window.statusBar()
    # Send a message
    window.show_status("Hello, APS.")


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
