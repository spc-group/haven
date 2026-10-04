import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from functools import partial

from ophyd_async.core import Device
from qasync import asyncSlot
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from firefly.component_selector import ComponentSelector
from firefly.plans import display
from firefly.plans.regions import (
    RegionsManager,
    device_parameters,
    make_relative,
    update_device_parameters,
)

log = logging.getLogger()


class MotorRegionsManager(RegionsManager):
    default_precision = 5
    is_relative: bool

    @dataclass(frozen=True)
    class WidgetSet:
        active_checkbox: QCheckBox
        device_selector: ComponentSelector
        destination_input: QWidget

    @dataclass(frozen=True, eq=True)
    class Region:
        is_active: bool
        device: str
        position: float

    def widgets_to_region(self, widgets: WidgetSet) -> Region:
        """Take a list of widgets in a row, and build a Region object."""
        device_name = widgets.device_selector.selected_device_path()
        destination_input = widgets.destination_input
        if isinstance(destination_input, QComboBox):
            destination = destination_input.currentData()
        elif isinstance(destination_input, QLineEdit):
            destination = destination_input.text()
        else:
            destination = destination_input.value()
        return self.Region(
            is_active=widgets.active_checkbox.isChecked(),
            device=device_name,
            position=destination,
        )

    async def create_row_widgets(self, row: int) -> list[QWidget]:
        # Component selector
        device_selector = ComponentSelector()
        device_selector.device_selected.connect(
            partial(self.update_device_parameters, row=row)
        )
        # start point
        destination_input = QDoubleSpinBox()
        destination_input.lineEdit().setPlaceholderText("Position…")
        destination_input.setMinimum(float("-inf"))
        destination_input.setMaximum(float("inf"))
        destination_input.setMinimumWidth(100)

        # Add widgets to the layout
        return [
            device_selector,
            destination_input,
        ]

    async def update_devices(self, registry=None, *, rows: Sequence[int] | None = None):
        registry = await super().update_devices(registry)
        if registry is None:
            return

        rows = self.row_numbers if rows is None else rows
        widgetsets = [self.row_widgets(row=row) for row in rows]
        aws = [
            widgets.device_selector.update_devices(registry) for widgets in widgetsets
        ]
        await asyncio.gather(*aws)
        return registry

    @asyncSlot(Device)
    async def update_device_parameters(self, device: Device, row: int):
        widgets = self.row_widgets(row=row)
        params = await device_parameters(device)
        destination_col = 2
        # Decide what kind of widget we need
        if issubclass(params.datatype, Enum):
            new_widget = QComboBox()
            for item in params.datatype:
                new_widget.addItem(f"{item.name} ({item.value})", item)
        elif params.datatype is float:
            new_widget = QDoubleSpinBox()
        elif params.datatype is int:
            new_widget = QSpinBox()
        else:
            new_widget = QLineEdit()
        # Replace the old widget with the new one
        old_widget = self.layout.itemAtPosition(row, destination_col).widget()
        self.layout.removeWidget(old_widget)
        old_widget.deleteLater()
        new_widget.setMinimumWidth(200)
        self.layout.addWidget(new_widget, row, destination_col, alignment=Qt.AlignTop)
        await update_device_parameters(
            device=device,
            widgets=[new_widget],
            is_relative=self.is_relative,
        )

    @asyncSlot(int)
    async def set_relative_position(self, is_relative: int):
        """Adjust the target position based on relative/aboslute mode."""
        self.is_relative = bool(is_relative)
        for row in self.row_numbers:
            widgets = self.row_widgets(row)
            device = widgets.device_selector.current_component()
            if device is None:
                continue
            await make_relative(
                device=device,
                widgets=[widgets.destination_input],
                is_relative=self.is_relative,
            )


class MoveMotorDisplay(display.PlanStubDisplay):
    _default_region_count = 1
    scan_repetitions = 1

    def customize_ui(self):
        super().customize_ui()
        self.regions = MotorRegionsManager(layout=self.regions_layout)
        self.num_regions_spin_box.valueChanged.connect(self.regions.set_region_count)
        self.num_regions_spin_box.setValue(self._default_region_count)
        self.enable_all_checkbox.stateChanged.connect(self.regions.enable_all_rows)
        self.relative_scan_checkbox.stateChanged.connect(
            self.regions.set_relative_position
        )

    async def update_devices(self, registry):
        await super().update_devices(registry)
        await self.regions.update_devices(registry)

    def plan_args(self) -> tuple[tuple, dict]:
        # Get parameters from each row of line regions
        region_args = [(region.device, region.position) for region in self.regions]
        args = tuple(arg for region in region_args for arg in region)
        kwargs: dict[str, float] = {}
        return args, kwargs

    @property
    def plan_type(self):
        if self.ui.relative_scan_checkbox.isChecked():
            return "mvr"
        else:
            return "mv"

    def ui_filename(self):
        return "plans/move.ui"


# -----------------------------------------------------------------------------
# :author:    Juanjuan Huang
# :email:     juanjuan.huang@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
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
