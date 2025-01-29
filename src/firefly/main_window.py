import logging
import warnings
from pathlib import Path
from typing import Sequence

import qtawesome as qta
from pydm import data_plugins
from pydm.main_window import PyDMMainWindow
from qtpy import QtGui, QtWidgets

from firefly.queue_client import is_in_use
from haven import load_config

log = logging.getLogger(__name__)


class FireflyMainWindow(PyDMMainWindow):
    """A main window that will hold the various pydm displays.

    Parameters
    ==========
    actions
      A ActionsRegistry object. Will be used to run
      ``self.setup_menu_actions``.

    """

    hide_nav_bar: bool = False

    def __init__(
        self,
        actions=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.setup_ui()
        if actions is not None:
            self.setup_menu_actions(actions)

    def setup_ui(self):
        # Hide the navbar initially
        self.ui.navbar.setVisible(False)
        # Add window icon
        root_dir = Path(__file__).parent.absolute()
        icon_path = root_dir / "splash.png"
        self.setWindowIcon(QtGui.QIcon(str(icon_path)))
        # Hide the nav bar
        if self.hide_nav_bar:
            self.toggle_nav_bar(False)
            self.ui.actionShow_Navigation_Bar.setChecked(False)
        # Prepare the status bar
        bar = self.statusBar()
        _label = QtWidgets.QLabel()
        _label.setText("Queue:")
        bar.addPermanentWidget(_label)
        self.ui.queue_length_label = QtWidgets.QLabel()
        self.ui.queue_length_label.setToolTip(
            "The length of the queue, not including the running plan."
        )
        self.ui.queue_length_label.setText("(??)")
        bar.addPermanentWidget(self.ui.queue_length_label)
        self.ui.environment_label = QtWidgets.QLabel()
        self.ui.environment_label.setToolTip(
            "The current state of the queue server environment."
        )
        self.ui.environment_label.setText("N/A")
        bar.addPermanentWidget(self.ui.environment_label)
        _label = QtWidgets.QLabel()
        _label.setText("/")
        bar.addPermanentWidget(_label)
        self.ui.re_label = QtWidgets.QLabel()
        self.ui.re_label.setToolTip("The current state of the queue server run engine.")
        self.ui.re_label.setText("N/A")
        bar.addPermanentWidget(self.ui.re_label)
        # Create menu bars (actual menu entries are set later)
        ## Setup menu
        self.ui.setup_menu = QtWidgets.QMenu(self.ui.menubar)
        self.ui.setup_menu.setObjectName("setup_menu")
        self.ui.setup_menu.setTitle("Set&up")
        self.ui.menubar.addAction(self.ui.setup_menu.menuAction())
        # Menu for managing the Queue server
        self.ui.queue_menu = QtWidgets.QMenu(self.ui.menubar)
        self.ui.queue_menu.setObjectName("menuQueue")
        self.ui.queue_menu.setTitle("&Queue")
        self.ui.menubar.addAction(self.ui.queue_menu.menuAction())
        ## Positioners menu
        self.ui.positioners_menu = QtWidgets.QMenu(self.ui.menubar)
        self.ui.positioners_menu.setObjectName("menuPositioners")
        self.ui.positioners_menu.setTitle("&Positioners")
        self.ui.menubar.addAction(self.ui.positioners_menu.menuAction())
        ## Scans menu
        self.ui.plans_menu = QtWidgets.QMenu(self.ui.menubar)
        self.ui.plans_menu.setObjectName("plans_menu")
        self.ui.plans_menu.setTitle("&Plans")
        self.ui.menubar.addAction(self.ui.plans_menu.menuAction())
        ## Detectors menu
        self.ui.detectors_menu = QtWidgets.QMenu(self.ui.menubar)
        self.ui.detectors_menu.setObjectName("detectors_menu")
        self.ui.detectors_menu.setTitle("&Detectors")
        self.ui.menubar.addAction(self.ui.detectors_menu.menuAction())
        # Connect signals to the status bar
        ...

    async def update_devices(self, registry):
        self.registry = registry
        await self.display_widget().update_devices(registry)

    def update_queue_controls(self, new_status):
        """Update the queue controls to match the state of the queueserver."""
        pass

    def update_queue_status(self, status):
        """Update the queue status labels."""
        worker_state = status.get("worker_environment_state", "—")
        self.ui.environment_label.setText(worker_state)
        new_length = status.get("items_in_queue", "—")
        self.ui.queue_length_label.setText(f"({new_length})")
        self.ui.re_label.setText(status.get("re_state", "—"))
        # Notify the display of the new status
        display = self.display_widget()
        display.update_queue_status(status)

    def open(self, *args, **kwargs):
        widget = super().open(*args, **kwargs)
        # Connect signals for showing message in the window's status bar
        try:
            widget.status_message_changed.connect(self.show_status)
        except AttributeError:
            msg = (
                f"No status messages on window: {args}, {kwargs}. "
                "Possibly you're not using FireflyMainWindow "
                "or FireflyDisplay?"
            )
            log.warning(msg)
            warnings.warn(msg)
        # Add the caQtDM action to the menubar
        caqtdm_menu = self.ui.setup_menu
        caqtdm_actions = getattr(widget, "caqtdm_actions", [])
        if len(caqtdm_actions) > 0:
            caqtdm_menu.addSeparator()
        for action in caqtdm_actions:
            action.setIcon(qta.icon("fa5s.wrench"))
            caqtdm_menu.addAction(action)

    def closeEvent(self, event):
        super().closeEvent(event)
        # Delete the window so it's recreated next time it's opened
        self.deleteLater()

    def add_menu_action(self, action_name: str, text: str, menu: QtWidgets.QMenu):
        """Add a new QAction to a menubar menu.

        The action triggers when the menu item is activated.

        Parameters
        ==========
        action_name
          The name of the parameter to the save the action. Will be
          accessible via *action_name* on the window, and window.ui.
        text
          Human-readable text to show on the menu item.
        menu
          The QMenu object in which to put this menu item.

        Returns
        =======
        action
          A QAction for the menu item.

        """
        action = QtWidgets.QAction(self)
        action.setObjectName(action_name)
        action.setText(text)
        menu.addAction(action)
        # Save the action as object parameters
        setattr(self.ui, action_name, action)
        setattr(self, action_name, action)
        return action

    def setup_menu_actions(self, actions):
        self._setup_menu_actions(
            logs_window_action=actions.log,
            queue_monitor=actions.queue_monitor,
            queue_control_actions=actions.queue_controls,
            queue_settings_actions=actions.queue_settings,
            energy_window_action=actions.energy,
            filters_action=actions.xray_filter,
            slits_actions=actions.slits,
            mirror_actions=actions.mirrors,
            table_actions=actions.tables,
            robot_actions=actions.robots,
            plan_actions=actions.plans,
            run_browser_action=actions.run_browser,
            voltmeters_action=actions.voltmeter,
            motor_actions=actions.motors,
            ion_chamber_actions=actions.ion_chambers,
            camera_actions=actions.cameras,
            area_detector_actions=actions.area_detectors,
            xrf_detector_actions=actions.xrf_detectors,
            status_window_action=actions.status,
            bss_window_action=actions.bss,
            iocs_window_action=actions.iocs,
        )

    def _setup_menu_actions(
        self,
        logs_window_action,
        queue_monitor,
        queue_control_actions,
        queue_settings_actions,
        energy_window_action,
        filters_action,
        slits_actions,
        mirror_actions,
        table_actions,
        robot_actions,
        plan_actions,
        run_browser_action,
        voltmeters_action,
        motor_actions,
        ion_chamber_actions,
        camera_actions,
        area_detector_actions,
        xrf_detector_actions,
        status_window_action,
        bss_window_action,
        iocs_window_action,
    ):
        # Log viewer window
        if logs_window_action is not None:
            self.ui.menuView.addAction(logs_window_action)
        # Menu for managing the Queue server
        for action in queue_control_actions.values():
            self.ui.queue_menu.addAction(action)
        self.ui.queue_menu.addSeparator()
        # Queue settings for the queue client
        for action in queue_settings_actions.values():
            self.ui.queue_menu.addAction(action)
        self.ui.queue_menu.addAction(queue_monitor)
        # Sample viewer
        self.add_menu_action(
            action_name="actionShow_Sample_Viewer",
            text="Sample",
            menu=self.ui.positioners_menu,
        )
        # Motors sub-menu
        self.ui.motors_menu = QtWidgets.QMenu(self.ui.menubar)
        self.ui.motors_menu.setObjectName("motors_menu")
        self.ui.motors_menu.setTitle("Extra &Motors")
        motors_action = self.ui.motors_menu.menuAction()
        self.ui.positioners_menu.addAction(motors_action)
        motors_action.setIcon(qta.icon("mdi.cog-clockwise"))
        # Add actions to the motors sub-menus
        for action in motor_actions.values():
            self.ui.motors_menu.addAction(action)
        # Menu to launch the Window to change energy
        self.ui.positioners_menu.addAction(energy_window_action)
        # Add optical components
        if filters_action is not None:
            self.ui.positioners_menu.addAction(filters_action)
        if len(slits_actions) > 0:
            self.ui.positioners_menu.addSection("Slits")
        for action in slits_actions.values():
            self.ui.positioners_menu.addAction(action)
        if len(mirror_actions) > 0:
            self.ui.positioners_menu.addSection("Mirrors")
        for action in mirror_actions.values():
            self.ui.positioners_menu.addAction(action)
        if len(table_actions) > 0:
            self.ui.positioners_menu.addSection("Tables")
        for action in table_actions.values():
            self.ui.positioners_menu.addAction(action)
        if len(robot_actions) > 0:
            self.ui.positioners_menu.addSection("Robots")
        for action in robot_actions.values():
            self.ui.positioners_menu.addAction(action)
        # Add actions to the individual plans
        for action in plan_actions.values():
            self.ui.plans_menu.addAction(action)
        # Add entries for general scan management
        self.ui.plans_menu.addSeparator()
        if run_browser_action is not None:
            self.ui.plans_menu.addAction(run_browser_action)
        # Voltmeters window
        if voltmeters_action is not None:
            self.ui.detectors_menu.addAction(voltmeters_action)
        # Add an ion chamber sub-menu
        if len(ion_chamber_actions) > 0:
            self.ui.ion_chambers_menu = QtWidgets.QMenu(self.ui.menubar)
            self.ui.ion_chambers_menu.setObjectName("ion_chambers_menu")
            self.ui.ion_chambers_menu.setTitle("&Ion Chambers")
            self.ui.detectors_menu.addAction(self.ui.ion_chambers_menu.menuAction())
            # Add actions for the individual ion chambers
            for action in ion_chamber_actions.values():
                self.ui.ion_chambers_menu.addAction(action)
        # Cameras sub-menu
        self.ui.menuCameras = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuCameras.setObjectName("menuCameras")
        self.ui.menuCameras.setTitle("Cameras")
        self.ui.detectors_menu.addAction(self.ui.menuCameras.menuAction())
        # Add actions to the cameras sub-menus
        for action in camera_actions.values():
            self.ui.menuCameras.addAction(action)
        # Add area detectors to detectors menu
        if len(area_detector_actions) > 0:
            self.ui.detectors_menu.addSeparator()
        for action in area_detector_actions.values():
            self.ui.detectors_menu.addAction(action)
        # Add XRF detectors to detectors menu
        if len(xrf_detector_actions) > 0:
            self.ui.detectors_menu.addSeparator()
        for action in xrf_detector_actions.values():
            self.ui.detectors_menu.addAction(action)
        # Add other menu actions
        if status_window_action is not None:
            self.ui.menuView.addAction(status_window_action)
        if bss_window_action is not None:
            self.ui.setup_menu.addAction(bss_window_action)
        if iocs_window_action is not None:
            self.ui.setup_menu.addAction(iocs_window_action)
        # Make tooltips show up for menu actions
        for menu in [self.ui.setup_menu, self.ui.detectors_menu, self.ui.queue_menu]:
            menu.setToolTipsVisible(True)

    def show_status(self, message, timeout=0):
        """Show a message in the status bar."""
        bar = self.statusBar()
        bar.showMessage(message, timeout)

    def update_window_title(self):
        if self.showing_file_path_in_title_bar:
            title = self.current_file()
        else:
            title = self.display_widget().windowTitle()
        # Add the beamline name
        config = load_config()
        beamline_name = config["beamline"]["name"]
        title += f" - {beamline_name} - Firefly"
        if data_plugins.is_read_only():
            title += " [Read Only Mode]"
        self.setWindowTitle(title)


class PlanMainWindow(FireflyMainWindow):
    """A Qt window that has extra controls for a bluesky runengine."""

    navbar_actions: Sequence[str] = [
        "start",
        "|",
        "pause",
        "pause_now",
        "stop_queue",
        "|",
        "resume",
        "stop_runengine",
        "abort",
    ]

    hide_nav_bar: bool = True

    def setup_navbar(self, queue_control_actions):
        # Remove previous navbar actions
        navbar = self.ui.navbar
        for action in navbar.actions():
            navbar.removeAction(action)
        # Add runengine actions
        for key in self.navbar_actions:
            if key == "|":
                navbar.addSeparator()
            elif key in queue_control_actions:
                navbar.addAction(queue_control_actions[key])

    def update_queue_status(self, status):
        super().update_queue_status(status)
        # Apply style to the queue button (assuming it's called ``run_button``).
        display = self.display_widget()
        try:
            display.ui.run_button.update_queue_style(status)
        except AttributeError:
            pass

    def setup_menu_actions(self, actions):
        super().setup_menu_actions(actions=actions)
        self.setup_navbar(queue_control_actions=actions.queue_controls)

    def update_queue_controls(self, new_status):
        """Update the queue controls to match the state of the queueserver."""
        super().update_queue_controls(new_status)
        self.ui.navbar.setVisible(is_in_use(new_status))


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
