import asyncio
import logging
from dataclasses import dataclass
from functools import partial

from ophyd_async.core import Device
from qasync import asyncSlot
from qtpy.QtWidgets import QCheckBox, QDoubleSpinBox, QWidget

from firefly.component_selector import ComponentSelector
from firefly.plans import plan_display
from firefly.plans.regions import (
    RegionsManager,
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
        position_spin_box: QDoubleSpinBox

    @dataclass(frozen=True, eq=True)
    class Region:
        is_active: bool
        device: str
        position: float

    def widgets_to_region(self, widgets: WidgetSet) -> Region:
        """Take a list of widgets in a row, and build a Region object."""
        device_name = widgets.device_selector.selected_device_path()
        return self.Region(
            is_active=widgets.active_checkbox.isChecked(),
            device=device_name,
            position=widgets.position_spin_box.value(),
        )

    async def create_row_widgets(self, row: int) -> list[QWidget]:
        # Component selector
        device_selector = ComponentSelector()
        device_selector.device_selected.connect(
            partial(self.update_device_parameters, row=row)
        )
        # start point
        position_spin_box = QDoubleSpinBox()
        position_spin_box.lineEdit().setPlaceholderText("Position…")
        position_spin_box.setMinimum(float("-inf"))
        position_spin_box.setMaximum(float("inf"))

        # Add widgets to the layout
        return [
            device_selector,
            position_spin_box,
        ]

    async def update_devices(self, registry):
        widgetsets = [self.row_widgets(row=row) for row in self.row_numbers]
        aws = [
            widgets.device_selector.update_devices(registry) for widgets in widgetsets
        ]
        await asyncio.gather(*aws)

    @asyncSlot(Device)
    async def update_device_parameters(self, device: Device, row: int):
        widgets = self.row_widgets(row=row)
        await update_device_parameters(
            device=device,
            widgets=[widgets.position_spin_box],
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
                widgets=[widgets.position_spin_box],
                is_relative=self.is_relative,
            )


class MoveMotorDisplay(plan_display.PlanStubDisplay):
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
        return "plans/move_motor_window.ui"


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
