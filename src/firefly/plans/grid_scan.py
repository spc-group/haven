import logging
import math

import numpy as np
from bluesky_queueserver_api import BPlan
from ophyd_async.core import Device
from qasync import asyncSlot
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from haven import sanitize_name

from firefly.component_selector import ComponentSelector
from firefly.plans.regions_display import (
    DeviceParameters,
    RegionBase,
    RegionsDisplay,
    device_parameters,
)

log = logging.getLogger()


class GridScanRegion(RegionBase):
    is_relative: bool

    def setup_ui(self):
        # motor No.
        self.motor_label = QtWidgets.QLabel()
        self.motor_label.setText(str(self.row - 1))
        # ComponentSelector
        self.motor_box = ComponentSelector()
        self.motor_box.device_selected.connect(self.update_device_parameters)
        # Start point
        self.start_line_edit = QtWidgets.QDoubleSpinBox()
        self.start_line_edit.setMinimum(float("-inf"))
        self.start_line_edit.setMaximum(float("inf"))
        # Stop point
        self.stop_line_edit = QtWidgets.QDoubleSpinBox()
        self.stop_line_edit.setMinimum(float("-inf"))
        self.stop_line_edit.setMaximum(float("inf"))
        # Number of scan points
        self.scan_pts_spin_box = QtWidgets.QSpinBox()
        self.scan_pts_spin_box.setMinimum(2)
        self.scan_pts_spin_box.setMaximum(99999)
        # Step size (non-editable)
        self.step_line_edit = QtWidgets.QLineEdit()
        self.step_line_edit.setReadOnly(True)
        self.step_line_edit.setDisabled(True)
        self.step_line_edit.setPlaceholderText("Step Size…")
        # Snake checkbox
        self.snake_checkbox = QtWidgets.QCheckBox()
        self.snake_checkbox.setText("Snake")
        self.snake_checkbox.setEnabled(True)
        # Fly checkbox # not available right now
        self.fly_checkbox = QtWidgets.QCheckBox()
        self.fly_checkbox.setText("Fly")
        self.fly_checkbox.setEnabled(False)
        # Connect signals
        self.start_line_edit.textChanged.connect(self.update_step_size)
        self.stop_line_edit.textChanged.connect(self.update_step_size)
        self.scan_pts_spin_box.valueChanged.connect(self.update_step_size)
        self.scan_pts_spin_box.valueChanged.connect(self.num_points_changed)

        # Add all widgets to the layout
        self.widgets = [
            self.motor_label,
            self.motor_box,
            self.start_line_edit,
            self.stop_line_edit,
            self.scan_pts_spin_box,
            self.step_line_edit,
            self.snake_checkbox,
            self.fly_checkbox,
        ]
        for column, widget in enumerate(self.widgets):
            self.layout.addWidget(widget, self.row, column, alignment=Qt.AlignTop)

        # Connect Qt signals/slots
        self.scan_pts_spin_box.valueChanged.connect(self.num_points_changed)

    @asyncSlot(Device)
    async def update_device_parameters(self, new_device: Device):
        device = await device_parameters(new_device)
        # Filter out non-numeric datatypes
        for widget in [self.start_line_edit, self.stop_line_edit]:
            widget.setEnabled(device.is_numeric)
            widget.setEnabled(device.is_numeric)
            # Set other metadata
            self.set_limits(device)
            widget.setDecimals(device.precision)
            # Handle units
            widget.setSuffix(f" {device.units}")
            # Set starting motor position
            if self.is_relative:
                widget.setValue(0)
            else:
                widget.setValue(device.current_value)

    def set_limits(self, device: DeviceParameters):
        """Set limits on the spin boxes to match the device limits."""
        if self.is_relative:
            minimum = device.minimum - device.current_value
            maximum = device.maximum - device.current_value
        else:
            maximum, minimum = device.maximum, device.minimum
        self.start_line_edit.setMaximum(maximum)
        self.start_line_edit.setMinimum(minimum)
        self.stop_line_edit.setMaximum(maximum)
        self.stop_line_edit.setMinimum(minimum)

    @asyncSlot(int)
    async def set_relative_position(self, is_relative: int):
        """Adjust the target position based on relative/aboslute mode."""
        self.is_relative = bool(is_relative)
        device = self.motor_box.current_component()
        if device is None:
            return
        params = await device_parameters(device)
        # Get last values first to avoid limit crossing
        widgets = [self.start_line_edit, self.stop_line_edit]
        if is_relative:
            new_positions = [
                widget.value() - params.current_value for widget in widgets
            ]
        else:
            new_positions = [
                widget.value() + params.current_value for widget in widgets
            ]
        # Update the current limits and positions
        self.set_limits(params)
        for widget, new_position in zip(widgets, new_positions):
            widget.setValue(new_position)

    def update_step_size(self):
        try:
            # Get Start and Stop values
            start_text = self.start_line_edit.text().strip()
            stop_text = self.stop_line_edit.text().strip()
            if not start_text or not stop_text:
                self.step_line_edit.setText("N/A")
                return

            start = float(start_text)
            stop = float(stop_text)

            # Ensure num_points is an integer
            num_points = int(self.scan_pts_spin_box.value())  # Corrected method call

            # Calculate step size
            if num_points > 1:
                step_size = (stop - start) / (num_points - 1)
                self.step_line_edit.setText(f"{step_size:.5g}")
            else:
                self.step_line_edit.setText("N/A")
        except ValueError:
            self.step_line_edit.setText("N/A")


class GridScanDisplay(RegionsDisplay):
    Region = GridScanRegion
    default_num_regions = 2

    def __init__(self, parent=None, args=None, macros=None, ui_filename=None, **kwargs):
        super().__init__(parent, args, macros, ui_filename, **kwargs)

    def customize_ui(self):
        super().customize_ui()
        self.update_snakes()
        # Connect scan points change to update total time
        self.ui.spinBox_repeat_scan_num.valueChanged.connect(self.update_total_time)
        self.scan_time_changed.connect(self.scan_duration_label.set_seconds)
        self.total_time_changed.connect(self.total_duration_label.set_seconds)
        # Default metadata values
        self.ui.comboBox_purpose.lineEdit().setPlaceholderText(
            "e.g. commissioning, alignment…"
        )
        self.ui.comboBox_purpose.setCurrentText("")

    def scan_durations(self, detector_time: float) -> tuple[float, float]:
        num_points = math.prod(
            [region.scan_pts_spin_box.value() for region in self.regions]
        )
        time_per_scan = detector_time * num_points
        num_scan_repeat = self.ui.spinBox_repeat_scan_num.value()
        total_time = num_scan_repeat * time_per_scan
        return time_per_scan, total_time

    @asyncSlot()
    async def update_total_time(self):
        """Update the total scan time and display it."""
        acquire_times = await self.detectors_list.acquire_times()
        detector_time = max([*acquire_times, float("nan")])
        # Calculate time per scan
        time_per_scan, total_time = self.scan_durations(detector_time)
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
        return total_time_per_scan

    @asyncSlot(object)
    async def update_devices_slot(self, registry):
        await super().update_devices(registry)
        await self.detectors_list.update_devices(registry)

    @asyncSlot(int)
    async def update_regions_slot(self, new_region_num: int):
        await super().update_regions(new_region_num)
        self.update_snakes()

    def update_snakes(self):
        """Update the snake checkboxes.

        The last region is not snakable, so that checkbox gets
        disabled and unchecked. The rest get enabled.

        """
        if len(self.regions) > 0:
            self.regions[-1].snake_checkbox.setEnabled(False)
            self.regions[-1].snake_checkbox.setChecked(False)
            for region_i in self.regions[:-1]:
                region_i.snake_checkbox.setEnabled(True)

    def get_scan_parameters(self):
        # Get paramters from each rows of line regions:
        motor_lst, start_lst, stop_lst, num_points_lst = [], [], [], []
        for region_i in reversed(self.regions):
            motor_lst.append(region_i.motor_box.current_component().name)
            start_lst.append(float(region_i.start_line_edit.text()))
            stop_lst.append(float(region_i.stop_line_edit.text()))
            num_points_lst.append(int(region_i.scan_pts_spin_box.value()))

        motor_args = [
            values
            for motor_i in zip(motor_lst, start_lst, stop_lst, num_points_lst)
            for values in motor_i
        ]

        return detectors, motor_args, repeat_scan_num

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
        # Get parameters from each row of line regions:
        device_names = [region.motor_box.current_component().name for region in self.regions]
        device_names = [sanitize_name(name) for name in device_names]
        start_points = [region.start_line_edit.value() for region in self.regions]
        stop_points = [region.stop_line_edit.value() for region in self.regions]
        num_points = [region.scan_pts_spin_box.value() for region in self.regions]
        device_args = [
            values
            for line in zip(device_names, start_points, stop_points, num_points)
            for values in line
        ]
        # Decide whether and how to snake the axes
        # get snake axes, if all unchecked, set it None
        snake_axes = [
            region.motor_box.current_component().name
            for region in self.regions
            if region.snake_checkbox.isChecked()
        ]
        if snake_axes == []:
            snake_axes = False
        
        # Prepare the argument collections
        args = (detectors, *device_args)
        kwargs = {
            "snake_axes": snake_axes,
            "md": self.get_meta_data()
        }
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
