import logging
from typing import Mapping

import qtawesome as qta
from pydm import PyDMChannel
from pydm.widgets import PyDMByteIndicator, PyDMPushButton
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QHBoxLayout, QSizePolicy

from firefly import display
from haven.devices.shutter import ShutterState

log = logging.getLogger(__name__)


def name_to_title(name: str):
    """Convert a python-valid Ophyd object name to a human-readable
    title-case string.

    """
    title = name.replace("_", " ").title()
    return title


class StatusDisplay(display.FireflyDisplay):
    first_shutter_row = 3
    bss_window_requested = Signal()

    async def update_devices(self, registry):
        await super().update_devices(registry)
        shutters = registry.findall("shutters", allow_none=True)
        shutters = sorted(shutters, key=lambda x: x.name)
        self.remove_shutter_widgets()
        for shutter in shutters:
            self.add_shutter_widgets(shutter)

    def remove_shutter_widgets(self):
        # Disconnect existing pydm channels for the openable/closable signals
        old_channels = [ch for chs in self.shutter_channels for ch in chs]
        old_channels = [ch for ch in old_channels if ch is not None]
        for ch in old_channels:
            ch.disconnect()
        self.shutter_channels = []

    def add_shutter_widgets(self, shutter):
        # Add widgets for shutters
        on_color = self.ui.shutter_permit_indicator.onColor
        off_color = self.ui.shutter_permit_indicator.offColor
        # Add a layout with the buttons
        layout = QHBoxLayout()
        label = name_to_title(shutter.name) + ":"
        row_idx = self.first_shutter_row + len(self.shutter_channels)
        self.beamline_layout.insertRow(row_idx, label, layout)
        # Indicator to show if the shutter is open
        indicator = PyDMByteIndicator(
            parent=self, init_channel=f"haven://{shutter.name}.readback"
        )
        indicator.labels = ["Closed", "Fault"]
        indicator.numBits = 2
        indicator.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # Switch colors because open is 0 which should means "good"
        indicator.offColor = on_color
        indicator.onColor = off_color
        layout.addWidget(indicator)
        # Button to open the shutter
        open_btn = PyDMPushButton(
            parent=self,
            label="Open",
            icon=qta.icon("mdi.window-shutter-open"),
            pressValue=ShutterState.OPEN,
            relative=False,
            init_channel=f"haven://{shutter.name}.setpoint",
        )
        layout.addWidget(open_btn)
        if hasattr(shutter, "open_allowed"):
            openable_channel = PyDMChannel(
                address=f"haven://{shutter.name}.open_allowed",
                value_slot=open_btn.setEnabled,
            )
            openable_channel.connect()
        else:
            openable_channel = None
        # Button to close the shutter
        close_btn = PyDMPushButton(
            parent=self,
            label="Close",
            icon=qta.icon("mdi.window-shutter"),
            pressValue=ShutterState.CLOSED,
            relative=False,
            init_channel=f"haven://{shutter.name}.setpoint",
        )
        layout.addWidget(close_btn)
        if hasattr(shutter, "close_allowed"):
            closable_channel = PyDMChannel(
                address=f"haven://{shutter.name}.close_allowed",
                value_slot=close_btn.setEnabled,
            )
            closable_channel.connect()
        else:
            closable_channel = None
        self.shutter_channels.append((openable_channel, closable_channel))

    def update_bss_metadata(self, md: Mapping[str, str]):
        super().update_bss_metadata(md)
        self.ui.proposal_id_label.setText(md.get("proposal_id", ""))
        self.ui.proposal_title_label.setText(md.get("proposal_title", ""))
        self.ui.esaf_id_label.setText(md.get("esaf_id", ""))
        self.ui.esaf_title_label.setText(md.get("esaf_title", ""))
        self.ui.esaf_status_label.setText(md.get("esaf_status", ""))
        self.ui.esaf_end_date_label.setText(md.get("esaf_end", ""))
        self.ui.esaf_users_label.setText(md.get("esaf_users", ""))

    def customize_ui(self):
        self.ui.bss_modify_button.clicked.connect(self.bss_window_requested.emit)
        self.ui.bss_modify_button.setIcon(qta.icon("fa6s.calendar"))
        # Remove existing designer shutter widgets
        self.beamline_layout.removeRow(self.ui.shutter_A_layout)
        self.beamline_layout.removeRow(self.ui.shutter_CD_layout)
        self.shutter_channels = []

    def ui_filename(self):
        return "status.ui"


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
