from firefly.main_window import FireflyMainWindow, PlanMainWindow


def test_navbar(ffapp):
    window = PlanMainWindow()
    # Check navbar actions on the app
    assert hasattr(ffapp, "pause_runengine_action")
    # Check that the navbar actions are set up properly
    assert hasattr(window.ui, "navbar")
    navbar = window.ui.navbar
    # Navigation actions are removed
    assert window.ui.actionHome not in navbar.actions()
    # Run engine actions have been added to the navbar
    assert ffapp.pause_runengine_action in navbar.actions()
    assert ffapp.start_queue_action in navbar.actions()


def test_navbar_autohide(ffapp, qtbot):
    """Test that the queue navbar is only visible when plans are queued."""
    window = PlanMainWindow()
    window.show()
    navbar = window.ui.navbar
    # Pretend the queue has some things in it
    with qtbot.waitSignal(ffapp.queue_length_changed):
        ffapp.queue_length_changed.emit(3)
    assert navbar.isVisible()
    # Make the queue be empty
    with qtbot.waitSignal(ffapp.queue_length_changed):
        ffapp.queue_length_changed.emit(0)
    assert not navbar.isVisible()


def test_add_menu_action(ffapp):
    window = FireflyMainWindow()
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


def test_customize_ui(ffapp):
    window = FireflyMainWindow()
    assert hasattr(window.ui, "menuScans")


def test_show_message(ffapp):
    window = FireflyMainWindow()
    status_bar = window.statusBar()
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
