import logging
import math
from collections.abc import Sequence
from functools import partial
from dataclasses import dataclass

import numpy as np
from ophyd_async.core import Device
from qasync import asyncSlot
from qtpy.QtWidgets import QWidget, QDoubleSpinBox, QSpinBox, QLabel, QCheckBox
from qtpy.QtCore import Qt, Signal, Slot

from firefly.component_selector import ComponentSelector
from firefly.plans.regions import RegionsManager, make_relative, DeviceParameters, update_device_parameters, set_limits
from firefly.plans.plan_display import PlanDisplay
from haven import sanitize_name

log = logging.getLogger()


class GridRegionsManager(RegionsManager):
    is_relative: bool = False
    
    # Signals
    num_points_changed = Signal(int)

    @dataclass(frozen=True)
    class WidgetSet():
        active_checkbox: QCheckBox
        device_selector: ComponentSelector
        start_spin_box: QDoubleSpinBox
        stop_spin_box: QDoubleSpinBox
        num_points_spin_box: QSpinBox
        step_label: QLabel
        snake_checkbox: QCheckBox
        fly_checkbox: QCheckBox

    @dataclass(frozen=True, eq=True)
    class Region():
        is_active: bool
        device: str
        start: float
        stop: float
        num_points: int
        snake: bool
    
    def widgets_to_region(self, widgets: WidgetSet) -> Region:
        """Take a list of widgets in a row, and build a Region object.

        """
        device_name = widgets.device_selector.current_device_name()
        return self.Region(
            is_active=widgets.active_checkbox.isChecked(),
            device=sanitize_name(device_name),
            start=widgets.start_spin_box.value(),
            stop=widgets.stop_spin_box.value(),
            num_points = widgets.num_points_spin_box.value(),
            snake = widgets.snake_checkbox.isChecked(),
        )
    
    async def create_row_widgets(self, row: int) -> list[QWidget]:
        # ComponentSelector
        device_selector = ComponentSelector()
        device_selector.device_selected.connect(self.update_device_parameters)
        # Start point
        start_spin_box = QDoubleSpinBox()
        start_spin_box.setMinimum(float("-inf"))
        start_spin_box.setMaximum(float("inf"))
        # Stop point
        stop_spin_box = QDoubleSpinBox()
        stop_spin_box.setMinimum(float("-inf"))
        stop_spin_box.setMaximum(float("inf"))
        # Number of scan points
        scan_pts_spin_box = QSpinBox()
        scan_pts_spin_box.setMinimum(2)
        scan_pts_spin_box.setValue(2)
        scan_pts_spin_box.setMaximum(99999)
        # Step size (non-editable)
        step_label = QLabel()
        step_label.setText("NaN")
        # Snake checkbox
        snake_checkbox = QCheckBox()
        snake_checkbox.setText("Snake")
        snake_checkbox.setEnabled(True)
        # Fly checkbox # not available right now
        fly_checkbox = QCheckBox()
        fly_checkbox.setText("Fly")
        fly_checkbox.setEnabled(False)
        # Connect signals
        update_step_size = partial(self.update_step_size, row=row)
        start_spin_box.valueChanged.connect(update_step_size)
        stop_spin_box.valueChanged.connect(update_step_size)
        scan_pts_spin_box.valueChanged.connect(update_step_size)
        scan_pts_spin_box.valueChanged.connect(self.update_num_points)
        # Add all widgets to the layout
        return [
            device_selector,
            start_spin_box,
            stop_spin_box,
            scan_pts_spin_box,
            step_label,
            snake_checkbox,
            fly_checkbox,
        ]

    @asyncSlot(Device)
    async def update_device_parameters(self, device: Device, row: int):
        """Update the *widgets*' properties based on a *device*."""
        widgets = self.row_widgets(row=row)
        await update_device_parameters(
            device=device,
            widgets=[widgets.start_spin_box, widgets.stop_spin_box],
            is_relative=self.is_relative
        )

    def update_num_points(self):
        self.num_points_changed.emit(self.num_points())

    def num_points(self):
        rows = self.row_numbers
        num_pts_col = 4
        spin_boxes = [self.layout.itemAtPosition(row, num_pts_col).widget() for row in rows]
        num_points = math.prod([box.value() for box in spin_boxes])
        return num_points

    # def set_num_regions(self, num: int):
    #     super().set_num_regions(num=num)
    #     self.update_snakes()

    # def update_snakes(self):
    #     """Update the snake checkboxes.

    #     The last region is not snakable, so that checkbox gets
    #     disabled and unchecked. The rest get enabled.

    #     """
    #     if len(self.regions) > 0:
    #         self.regions[-1].snake_checkbox.setEnabled(False)
    #         self.regions[-1].snake_checkbox.setChecked(False)
    #         for region_i in self.regions[:-1]:
    #             region_i.snake_checkbox.setEnabled(True)

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
                widgets=[widgets.start_spin_box, widgets.stop_spin_box],
                is_relative=is_relative,
            )

    @Slot()
    def update_step_size(self, row: int):
        widgets = self.row_widgets(row)
        start = widgets.start_spin_box.value()
        stop = widgets.stop_spin_box.value()
        num_points = widgets.num_points_spin_box.value()
        # Calculate step size
        precision = max(
            widgets.start_spin_box.decimals(), widgets.stop_spin_box.decimals()
        )
        try:
            step_size = (stop - start) / (num_points - 1)
            step_size = round(step_size, precision)
        except ValueError:
            widgets.step_label.setText("NaN")
        else:
            widgets.step_label.setText(str(step_size))


class GridScanDisplay(PlanDisplay):
    _default_region_count = 2

    def __init__(self, parent=None, args=None, macros=None, ui_filename=None, **kwargs):
        super().__init__(parent, args, macros, ui_filename, **kwargs)

    def customize_ui(self):
        super().customize_ui()
        self.regions = GridRegionsManager(layout=self.regions_layout)
        self.num_regions_spin_box.valueChanged.connect(self.regions.set_region_count)
        self.num_regions_spin_box.setValue(self._default_region_count)
        # Connect scan points change to update total time
        self.ui.spinBox_repeat_scan_num.valueChanged.connect(self.update_total_time)
        self.ui.detectors_list.selectionModel().selectionChanged.connect(
            self.update_total_time
        )
        self.scan_time_changed.connect(self.scan_duration_label.set_seconds)
        self.total_time_changed.connect(self.total_duration_label.set_seconds)

    async def scan_durations(self) -> tuple[float, float]:
        num_points = self.regions.num_points()
        acquire_times = await self.detectors_list.acquire_times()
        detector_time = max([*acquire_times, float("nan")])
        time_per_scan = num_points * detector_time
        num_scan_repeat = self.ui.spinBox_repeat_scan_num.value()
        total_time = num_scan_repeat * time_per_scan
        return time_per_scan, total_time

    @asyncSlot()
    async def update_total_time(self):
        """Update the total scan time and display it."""
        # Calculate time per scan
        time_per_scan, total_time = await self.scan_durations()
        self.scan_time_changed.emit(time_per_scan)
        self.total_time_changed.emit(total_time)

    def add_region(self):
        new_region = super().add_region()
        self.relative_scan_checkbox.stateChanged.connect(
            new_region.set_relative_position
        )
        new_region.set_relative_position(self.relative_scan_checkbox.checkState())
        return new_region

    def reset_default_regions(self):
        super().reset_default_regions()
        # Reset scan repeat num to 1
        self.ui.spinBox_repeat_scan_num.setValue(1)

    def time_per_scan(self, detector_time: float) -> float:
        total_num_pnts = np.prod(
            [region.scan_pts_spin_box.value() for region in self.regions]
        )
        total_time_per_scan = total_num_pnts * detector_time
        return float(total_time_per_scan)

    @asyncSlot(int)
    async def update_regions_slot(self, new_region_num: int):
        await super().update_regions(new_region_num)
        self.update_snakes()

    @property
    def plan_type(self):
        if self.ui.relative_scan_checkbox.isChecked():
            return "rel_grid_scan"
        else:
            return "grid_scan"

    @property
    def scan_repetitions(self) -> int:
        """How many times should each scan be run."""
        return self.ui.spinBox_repeat_scan_num.value()

    def plan_args(self):
        detectors = self.ui.detectors_list.selected_detectors()
        detector_names = [detector.name for detector in detectors]
        # Get parameters from each row of line regions:
        region_args = [
            (region.device, region.start, region.stop, region.num_points)
            for region in self.regions
        ]
        device_args = [arg for region in region_args for arg in region]
        # Decide whether and how to snake the axes
        # get snake axes, if all unchecked, set it None
        snake_axes = [region.device for region in self.regions if region.snake]
        if snake_axes == []:
            snake_axes = False
        # Prepare the argument collections
        args = (detector_names, *device_args)
        kwargs = {"snake_axes": snake_axes, "md": self.plan_metadata()}
        return args, kwargs

    def ui_filename(self):
        return "plans/grid_scan.ui"


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
