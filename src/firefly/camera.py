import logging
from enum import IntEnum
from pathlib import Path

# from pydm.data_plugins.epics_plugin import EPICSPlugin
from pydm.widgets.channel import PyDMChannel
from qtpy.QtCore import Slot
from qtpy.QtGui import QColor

from firefly import FireflyApplication, display

log = logging.getLogger(__name__)


class DetectorStates(IntEnum):
    IDLE = 0
    ACQUIRE = 1
    READOUT = 2
    CORRECT = 3
    SAVING = 4
    ABORTING = 5
    ERROR = 6
    WAITING = 7
    INITIALIZING = 8
    DISCONNECTED = 9
    ABORTED = 10


class AcquireStates(IntEnum):
    DONE = 0
    ACQUIRE = 1


class CameraDisplay(display.FireflyDisplay):
    prefix: str = ""
    properties_file: Path = Path("~/EPICS_AD_Viewer.properties").expanduser()
    _camera_state: int = DetectorStates.IDLE
    _camera_connected: bool = False

    def __init__(self, *, args=None, macros={}, **kwargs):
        self.prefix = macros.get("PREFIX", "")
        super().__init__(args=args, macros=macros, **kwargs)
        # Disconnect previous channels to the indicator
        byte = self.camera_status_indicator
        for ch in byte.channels():
            ch.disconnect()
        # Channel for watching the detector state
        self.detector_state = PyDMChannel(
            address=self.camera_status_label.channel,
            connection_slot=self.update_camera_connection,
            value_slot=self.update_camera_state,
        )
        self.detector_state.connect()
        byte._channels.append(self.detector_state)
        # Color for various states
        self._ioc_disconnected_color = QColor(255, 255, 255)
        self._detector_disconnected_color = QColor(255, 0, 0)
        self._idle_color = QColor(0, 255, 0)
        self._acquire_color = QColor(255, 255, 0)

    def customize_ui(self):
        # Connect button for opening the individual camera viewers
        app = FireflyApplication.instance()
        try:
            action = app.camera_actions[self.macros()["CAMERA"]]
        except (KeyError, AttributeError):
            pass
        else:
            self.ui.viewer_button.clicked.connect(action.trigger)

    def ui_filename(self):
        return "camera.ui"

    @Slot(int)
    def update_camera_state(self, new_state):
        self._camera_state = new_state
        self.update_status_indicators()

    @Slot(bool)
    def update_camera_connection(self, new_state):
        self._camera_connected = new_state
        self.update_status_indicators()

    def update_status_indicators(self):
        # Retrieve widgets we're going to change
        bit = self.camera_status_indicator._indicators[0]
        lbl = self.camera_status_label
        # Determine the new state of the camera
        ioc_is_disconnected = not self._camera_connected
        new_state = self._camera_state
        camera_is_idle = new_state == DetectorStates.IDLE
        camera_is_acquiring = new_state == DetectorStates.ACQUIRE
        # Update the widgets
        if ioc_is_disconnected:
            # IOC is not running or not available
            bit.setColor(self._ioc_disconnected_color)
            lbl.setVisible(False)
        elif camera_is_idle:
            # Camera is idle
            bit.setColor(self._idle_color)
            lbl.setVisible(False)
        elif camera_is_acquiring:
            bit.setColor(self._acquire_color)
            lbl.setVisible(False)
        else:
            # Camera is disconnected or in an otherwise unexpected state
            bit.setColor(self._detector_disconnected_color)
            lbl.setVisible(True)


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
