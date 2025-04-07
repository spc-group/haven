import logging

from bluesky_queueserver_api import BPlan
from ophyd_async.core import Device
from qasync import asyncSlot
from qtpy import QtWidgets

from firefly.component_selector import ComponentSelector
from firefly.plans.regions_display import (
    DeviceParameters,
    RegionBase,
    RegionsDisplay,
    device_parameters,
)

log = logging.getLogger()


class LineScanRegion(RegionBase):
    num_points: int = 2
    is_relative: bool

    def setup_ui(self):
        # Component selector
        self.motor_box = ComponentSelector()
        self.motor_box.device_selected.connect(self.update_device_parameters)
        # start point
        self.start_line_edit = QtWidgets.QDoubleSpinBox()
        self.start_line_edit.lineEdit().setPlaceholderText("Start…")
        self.start_line_edit.setMinimum(float("-inf"))
        self.start_line_edit.setMaximum(float("inf"))

        # Stop point
        self.stop_line_edit = QtWidgets.QDoubleSpinBox()
        self.stop_line_edit.lineEdit().setPlaceholderText("Stop…")
        self.stop_line_edit.setMinimum(float("-inf"))
        self.stop_line_edit.setMaximum(float("inf"))

        # Step size (non-editable)
        self.step_line_edit = QtWidgets.QDoubleSpinBox()
        self.step_line_edit.setReadOnly(True)
        self.step_line_edit.setDisabled(True)
        self.step_line_edit.setMinimum(float("-inf"))
        self.step_line_edit.setMaximum(float("inf"))
        self.step_line_edit.setDecimals(4)
        self.step_line_edit.lineEdit().setPlaceholderText("Step Size…")

        # Add widgets to the layout
        self.widgets = [
            self.motor_box,
            self.start_line_edit,
            self.stop_line_edit,
            self.step_line_edit,
        ]
        for column, widget in enumerate(self.widgets):
            self.layout.addWidget(widget, self.row, column)

        # Connect signals
        self.start_line_edit.valueChanged.connect(self.update_step_size)
        self.stop_line_edit.valueChanged.connect(self.update_step_size)

    async def update_devices(self, registry):
        await self.motor_box.update_devices(registry)

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

    def set_num_points(self, num_points):
        self.num_points = max(2, int(num_points))  # Ensure num_points is >= 2
        self.update_step_size()

    def update_step_size(self):
        # Get Start and Stop values
        start = self.start_line_edit.value()
        stop = self.stop_line_edit.value()
        # Calculate step size
        try:
            step_size = (stop - start) / (self.num_points - 1)
        except (ValueError, ZeroDivisionError):
            self.step_line_edit.setValue(float("nan"))
        else:
            self.step_line_edit.setValue(step_size)


class LineScanDisplay(RegionsDisplay):
    Region = LineScanRegion

    @asyncSlot(object)
    async def update_devices_slot(self, registry):
        await self.update_devices(registry)
        await self.detectors_list.update_devices(registry)

    def customize_ui(self):
        super().customize_ui()

        # Connect signals for total time updates
        self.ui.scan_pts_spin_box.valueChanged.connect(self.update_total_time)
        self.ui.detectors_list.selectionModel().selectionChanged.connect(
            self.update_total_time
        )
        for region in self.regions:
            self.ui.scan_pts_spin_box.valueChanged.connect(region.set_num_points)
        self.ui.spinBox_repeat_scan_num.valueChanged.connect(self.update_total_time)
        self.scan_time_changed.connect(self.scan_duration_label.set_seconds)
        self.total_time_changed.connect(self.total_duration_label.set_seconds)
        # Default metadata values
        self.ui.comboBox_purpose.lineEdit().setPlaceholderText(
            "e.g. commissioning, alignment…"
        )
        self.ui.comboBox_purpose.setCurrentText("")

    def scan_durations(self, detector_time):
        num_points = self.ui.scan_pts_spin_box.value()
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

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        detectors, motor_args, repeat_scan_num = self.get_scan_parameters()
        md = self.get_meta_data()
        num_points = self.ui.scan_pts_spin_box.value()
        # Check for what kind of scan we're running based on use input
        if self.ui.relative_scan_checkbox.isChecked():
            if self.ui.log_scan_checkbox.isChecked():
                scan_type = "rel_log_scan"
            else:
                scan_type = "rel_scan"
        else:
            if self.ui.log_scan_checkbox.isChecked():
                scan_type = "log_scan"
            else:
                scan_type = "scan"
        # Build the queue item
        item = BPlan(
            scan_type,
            detectors,
            *motor_args,
            num=num_points,
            md=md,
        )

        # Submit the item to the queueserver
        log.info(f"Adding line scan() plan to queue: {item}.")
        # repeat scans
        for i in range(repeat_scan_num):
            self.queue_item_submitted.emit(item)

    def ui_filename(self):
        return "plans/line_scan.ui"


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
