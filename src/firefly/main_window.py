import logging
import warnings
from pathlib import Path
from typing import Optional, Sequence

import qtawesome as qta
from pydm import data_plugins
from pydm.main_window import PyDMMainWindow
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QAction

from haven import load_config

log = logging.getLogger(__name__)


class FireflyMainWindow(PyDMMainWindow):
    """A main window that will hold the various pydm displays.

    Parameters
    ==========
    logs_window_action
      Action for showing the log viewer.
    queue_control_actions
      Actions for controlling the queue (e.g. start/pause). Will be
      added to navbar and queue mneu only.
    queue_settings_actions
      Actions for changing settings for the queue
      (e.g. autoplay). Will be added to queue mneu only.
    energy_window_action
      Action for showing the energy positioner window.
    filters_action
      Action for showing the display to control the filter devices.
    slits_actions
      Actions for showing the displays to control the slits.
    mirror_actions
      Actions for showing the displays to control the mirrors.
    table_actions
      Actions for showing the displays to control the tables.
    plan_actions
      Actions for showing the displays to execute plans.
    run_browser_action
      Action for showing the display to browse past Bluesky runs.
    voltmeters_action
      Action for showing the display for the ion chamber voltmeters.
    motor_actions
      Actions for showing the displays to control assorted motors.
    ion_chamber_actions
      Actions for showing the displays to control the ion chambers.
    cameras_window_action
      Actions for showing the display for an overview of the cameras.
    camera_actions
      Actions for showing the diplays to control the cameras.
    area_detector_actions
      Actions for showing the displays to control the area detectors.
    xrf_detector_actions
      Actions for showing the displays to control the fluorescence detectors.
    status_window_action
      Action for showing the display for the overall beamline status.
    bss_window_action
      Action for showing the display for the beamline scheduling system metadata.
    iocs_window_action
      Action for showing the display to start/stop the IOCs.
    """

    hide_nav_bar: bool = True

    def __init__(
        self,
        *args,
        logs_window_action: Optional[QAction] = None,
        queue_control_actions: Sequence[QAction] = [],
        queue_settings_actions: Sequence[QAction] = [],
        energy_window_action: Optional[QAction] = None,
        filters_action: Optional[QAction] = None,
        slits_actions: Sequence[QAction] = [],
        mirror_actions: Sequence[QAction] = [],
        table_actions: Sequence[QAction] = [],
        plan_actions: Sequence[QAction] = [],
        run_browser_action: Optional[QAction] = None,
        voltmeters_action: Optional[QAction] = None,
        motor_actions: Sequence[QAction] = [],
        ion_chamber_actions: Sequence[QAction] = [],
        cameras_window_action: Optional[QAction] = None,
        camera_actions: Sequence[QAction] = [],
        area_detector_actions: Sequence[QAction] = [],
        xrf_detector_actions: Sequence[QAction] = [],
        status_window_action: Optional[QAction] = None,
        bss_window_action: Optional[QAction] = None,
        iocs_window_action: Optional[QAction] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.customize_ui(
            logs_window_action=logs_window_action,
            queue_control_actions=queue_control_actions,
            queue_settings_actions=queue_settings_actions,
            energy_window_action=energy_window_action,
            filters_action=filters_action,
            slits_actions=slits_actions,
            mirror_actions=mirror_actions,
            table_actions=table_actions,
            plan_actions=plan_actions,
            run_browser_action=run_browser_action,
            voltmeters_action=voltmeters_action,
            motor_actions=motor_actions,
            ion_chamber_actions=ion_chamber_actions,
            cameras_window_action=cameras_window_action,
            camera_actions=camera_actions,
            area_detector_actions=area_detector_actions,
            xrf_detector_actions=xrf_detector_actions,
            status_window_action=status_window_action,
            bss_window_action=bss_window_action,
            iocs_window_action=iocs_window_action,
        )

    def update_queue_controls(self, new_status):
        """Update the queue controls to match the state of the queueserver."""
        pass

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
        caqtdm_menu = self.ui.menuSetup
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

    def customize_ui(
        self,
        logs_window_action,
        queue_control_actions,
        queue_settings_actions,
        energy_window_action,
        filters_action,
        slits_actions,
        mirror_actions,
        table_actions,
        plan_actions,
        run_browser_action,
        voltmeters_action,
        motor_actions,
        ion_chamber_actions,
        cameras_window_action,
        camera_actions,
        area_detector_actions,
        xrf_detector_actions,
        status_window_action,
        bss_window_action,
        iocs_window_action,
    ):
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
        # Connect signals to the status bar
        ...
        # Log viewer window
        if logs_window_action is not None:
            self.ui.menuView.addAction(logs_window_action)
        # Setup menu
        self.ui.menuSetup = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuSetup.setObjectName("menuSetup")
        self.ui.menuSetup.setTitle("Set&up")
        self.ui.menubar.addAction(self.ui.menuSetup.menuAction())
        # Menu for managing the Queue server
        self.ui.queue_menu = QtWidgets.QMenu(self.ui.menubar)
        self.ui.queue_menu.setObjectName("menuQueue")
        self.ui.queue_menu.setTitle("&Queue")
        self.ui.menubar.addAction(self.ui.queue_menu.menuAction())
        for action in queue_control_actions:
            self.ui.queue_menu.addAction(action)
        self.ui.queue_menu.addSeparator()
        # Queue settings for the queue client
        for action in queue_settings_actions:
            self.ui.queue_menu.addAction(action)
        # Positioners menu
        self.ui.positioners_menu = QtWidgets.QMenu(self.ui.menubar)
        self.ui.positioners_menu.setObjectName("menuPositioners")
        self.ui.positioners_menu.setTitle("&Positioners")
        self.ui.menubar.addAction(self.ui.positioners_menu.menuAction())
        # Sample viewer
        self.add_menu_action(
            action_name="actionShow_Sample_Viewer",
            text="Sample",
            menu=self.ui.positioners_menu,
        )
        # Motors sub-menu
        self.ui.menuMotors = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuMotors.setObjectName("menuMotors")
        self.ui.menuMotors.setTitle("Extra &Motors")
        motors_action = self.ui.menuMotors.menuAction()
        self.ui.positioners_menu.addAction(motors_action)
        motors_action.setIcon(qta.icon("mdi.cog-clockwise"))
        # Add actions to the motors sub-menus
        for action in motor_actions:
            self.ui.menuMotors.addAction(action)
        # Menu to launch the Window to change energy
        self.ui.positioners_menu.addAction(energy_window_action)
        # Add optical components
        if filters_action is not None:
            self.ui.positioners_menu.addAction(filters_action)
        if len(slits_actions) > 0:
            self.ui.positioners_menu.addSection("Slits")
        for action in slits_actions:
            self.ui.positioners_menu.addAction(action)
        if len(mirror_actions) > 0:
            self.ui.positioners_menu.addSection("Mirrors")
        for action in mirror_actions:
            self.ui.positioners_menu.addAction(action)
        if len(table_actions) > 0:
            self.ui.positioners_menu.addSection("Tables")
        for action in table_actions:
            self.ui.positioners_menu.addAction(action)
        # Scans menu
        self.ui.menuScans = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuScans.setObjectName("menuScans")
        self.ui.menuScans.setTitle("&Scans")
        self.ui.menubar.addAction(self.ui.menuScans.menuAction())
        # Add actions to the individual plans
        for action in plan_actions:
            self.ui.menuScans.addAction(action)
        # Add entries for general scan management
        self.ui.menuScans.addSeparator()
        if run_browser_action is not None:
            self.ui.menuScans.addAction(run_browser_action)
        # Detectors menu
        self.ui.detectors_menu = QtWidgets.QMenu(self.ui.menubar)
        self.ui.detectors_menu.setObjectName("detectors_menu")
        self.ui.detectors_menu.setTitle("&Detectors")
        self.ui.menubar.addAction(self.ui.detectors_menu.menuAction())
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
            for action in ion_chamber_actions.values:
                self.ui.ion_chambers_menu.addAction(action)
        # Cameras sub-menu
        self.ui.menuCameras = QtWidgets.QMenu(self.ui.menubar)
        self.ui.menuCameras.setObjectName("menuCameras")
        self.ui.menuCameras.setTitle("Cameras")
        self.ui.detectors_menu.addAction(self.ui.menuCameras.menuAction())
        # Add actions to the cameras sub-menus
        if cameras_window_action is not None:
            self.ui.menuCameras.addAction(cameras_window_action)
            self.ui.menuCameras.addSeparator()
        for action in camera_actions:
            self.ui.menuCameras.addAction(action)
        # Add area detectors to detectors menu
        if len(area_detector_actions) > 0:
            self.ui.detectors_menu.addSeparator()
        for action in area_detector_actions:
            self.ui.detectors_menu.addAction(action)
        # Add XRF detectors to detectors menu
        if len(xrf_detector_actions) > 0:
            self.ui.detectors_menu.addSeparator()
        for action in xrf_detector_actions:
            self.ui.detectors_menu.addAction(action)
        # Add other menu actions
        if status_window_action is not None:
            self.ui.menuView.addAction(status_window_action)
        if bss_window_action is not None:
            self.ui.menuSetup.addAction(bss_window_action)
        if iocs_window_action is not None:
            self.ui.menuSetup.addAction(iocs_window_action)

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

    hide_nav_bar: bool = True

    def setup_navbar(self, queue_control_actions):
        # Remove previous navbar actions
        navbar = self.ui.navbar
        for action in navbar.actions():
            navbar.removeAction(action)
        # Add runengine actions
        for action in queue_control_actions:
            navbar.addAction(action)

    def customize_ui(self, *args, queue_control_actions, **kwargs):
        super().customize_ui(*args, queue_control_actions=queue_control_actions, **kwargs)
        self.setup_navbar(queue_control_actions=queue_control_actions)
        # Connect signals/slots
        # app.queue_length_changed.connect(self.set_navbar_visibility)

    def update_queue_controls(self, new_status):
        """Update the queue controls to match the state of the queueserver."""
        super().update_queue_controls(new_status)
        qsize = new_status['items_in_queue']
        self.ui.navbar.setVisible(qsize > 0)

    # @QtCore.Slot(int)
    # def set_navbar_visibility(self, queue_length: int):
    #     """Determine whether to make the navbar be visible."""
    #     log.debug(f"Setting navbar visibility. Queue length: {queue_length}")
    #     navbar = self.ui.navbar
    #     navbar.setVisible(queue_length > 0)


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
