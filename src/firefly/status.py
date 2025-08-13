import logging
from typing import Mapping

import qtawesome as qta
from pydm.widgets import PyDMByteIndicator, PyDMPushButton
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QHBoxLayout, QSizePolicy

from firefly import display
from haven import beamline
from haven.devices.shutter import ShutterState

log = logging.getLogger(__name__)


def name_to_title(name: str):
    """Convert a python-valid Ophyd object name to a human-readable
    title-case string.

    """
    title = name.replace("_", " ").title()
    return title


class StatusDisplay(display.FireflyDisplay):
    bss_window_requested = Signal()

    def add_shutter_widgets(self):
        form = self.ui.beamline_layout
        # Remove existing layouts
        form.removeRow(self.ui.shutter_A_layout)
        form.removeRow(self.ui.shutter_CD_layout)
        # Add widgets for shutters
        shutters = beamline.devices.findall("shutters", allow_none=True)
        row_idx = 4
        on_color = self.ui.shutter_permit_indicator.onColor
        off_color = self.ui.shutter_permit_indicator.offColor
        for shutter in shutters[::-1]:
            # Add a layout with the buttons
            layout = QHBoxLayout()
            label = name_to_title(shutter.name) + ":"
            form.insertRow(row_idx, label, layout)
            # Indicator to show if the shutter is open
            indicator = PyDMByteIndicator(
                parent=self, init_channel=f"haven://{shutter.name}.readback"
            )
            # indicator.showLabels = False
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
            print(f"{shutter.name} - {getattr(shutter, 'allow_open', True)=}")
            open_btn.setEnabled(getattr(shutter, "allow_open", True))
            layout.addWidget(open_btn)
            # Button to close the shutter
            close_btn = PyDMPushButton(
                parent=self,
                label="Close",
                icon=qta.icon("mdi.window-shutter"),
                pressValue=ShutterState.CLOSED,
                relative=False,
                init_channel=f"haven://{shutter.name}.setpoint",
            )
            close_btn.setEnabled(getattr(shutter, "allow_close", True))
            layout.addWidget(close_btn)

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
        self.add_shutter_widgets()

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
