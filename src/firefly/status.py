import asyncio
import logging
from functools import partial

import qtawesome as qta
from ophyd_async.core import Device
from pydm.widgets import PyDMByteIndicator
from qasync import asyncSlot
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy

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
    shutter_buttons: list[tuple[QPushButton, QPushButton]]
    shutter_permit_timer: QTimer

    def __init__(self, *args, shutter_check_period: int | float = 1.0, **kwargs):
        self.shutter_buttons = []
        self._shutter_check_period = shutter_check_period
        super().__init__(*args, **kwargs)

    def __del__(self):
        timer = getattr(self, "shutter_permit_timer")
        if timer is not None:
            timer.stop()

    async def update_devices(self, registry):
        await super().update_devices(registry)
        shutters = registry.findall("shutters", allow_none=True)
        shutters = sorted(shutters, key=lambda x: x.name)
        for shutter in shutters:
            self.add_shutter_widgets(shutter)
        self.shutters = shutters

    @asyncSlot(Device, ShutterState)
    async def move_shutter(self, shutter: Device, position: ShutterState):
        await shutter.set(position)

    def add_shutter_widgets(self, shutter):
        # Add widgets for shutters
        on_color = self.ui.shutter_permit_indicator.onColor
        off_color = self.ui.shutter_permit_indicator.offColor
        # Add a layout with the buttons
        layout = QHBoxLayout()
        label = name_to_title(shutter.name) + ":"
        row_idx = self.first_shutter_row + len(self.shutter_buttons)
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
        open_btn = QPushButton(parent=self)
        open_btn.setText("Open")
        open_btn.setIcon(qta.icon("mdi.window-shutter-open"))
        layout.addWidget(open_btn)
        open_btn.clicked.connect(partial(self.move_shutter, shutter, ShutterState.OPEN))
        # Button to close the shutter
        close_btn = QPushButton(parent=self)
        close_btn.setText("Close")
        close_btn.setIcon(qta.icon("mdi.window-shutter"))
        layout.addWidget(close_btn)
        close_btn.clicked.connect(
            partial(self.move_shutter, shutter, ShutterState.CLOSED)
        )
        self.shutter_buttons.append([open_btn, close_btn])

    def customize_ui(self):
        # Remove existing designer shutter widgets
        self.beamline_layout.removeRow(self.ui.shutter_A_layout)
        self.beamline_layout.removeRow(self.ui.shutter_CD_layout)
        # Periodically check if the shutter permissions have changed
        self.shutter_permit_timer = QTimer(self)
        self.shutter_permit_timer.timeout.connect(self.update_shutter_permissions)
        self.shutter_permit_timer.start(int(1000 * self._shutter_check_period))

    @asyncSlot()
    async def update_shutter_permissions(self):
        async def get_permissions(shutter):
            try:
                permissions = await asyncio.gather(
                    shutter.movable_logic.open_allowed(),
                    shutter.movable_logic.close_allowed(),
                )
            except AttributeError:
                permissions = (True, True)
            return permissions

        coros = [get_permissions(shutter) for shutter in self.shutters]
        shutter_permissions = await asyncio.gather(*coros)

        for buttons, permissions in zip(self.shutter_buttons, shutter_permissions):
            open_btn, close_btn = buttons
            allow_open, allow_close = permissions
            open_btn.setEnabled(allow_open)
            close_btn.setEnabled(allow_close)

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
