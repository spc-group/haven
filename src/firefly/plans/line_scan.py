import logging

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
from haven import sanitize_name

log = logging.getLogger()


class LineScanRegion(RegionBase):
    num_points: int = 2
    is_relative: bool

    def setup_ui(self):
        # Component selector
        self.motor_box = ComponentSelector()
        self.motor_box.device_selected.connect(self.update_device_parameters)
        # start point
        self.start_spin_box = QtWidgets.QDoubleSpinBox()
        self.start_spin_box.lineEdit().setPlaceholderText("Start…")
        self.start_spin_box.setMinimum(float("-inf"))
        self.start_spin_box.setMaximum(float("inf"))

        # Stop point
        self.stop_spin_box = QtWidgets.QDoubleSpinBox()
        self.stop_spin_box.lineEdit().setPlaceholderText("Stop…")
        self.stop_spin_box.setMinimum(float("-inf"))
        self.stop_spin_box.setMaximum(float("inf"))

        # Step size (non-editable)
        self.step_label = QtWidgets.QLabel()
        self.step_label.setText("nan")

        # Add widgets to the layout
        self.widgets = [
            self.motor_box,
            self.start_spin_box,
            self.stop_spin_box,
            self.step_label,
        ]
        for column, widget in enumerate(self.widgets):
            self.layout.addWidget(widget, self.row, column)

        # Connect signals
        self.start_spin_box.valueChanged.connect(self.update_step_size)
        self.stop_spin_box.valueChanged.connect(self.update_step_size)

    async def update_devices(self, registry):
        await self.motor_box.update_devices(registry)

    @asyncSlot(Device)
    async def update_device_parameters(self, new_device: Device):
        device = await device_parameters(new_device)
        # Filter out non-numeric datatypes
        for widget in [self.start_spin_box, self.stop_spin_box]:
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
        self.start_spin_box.setMaximum(maximum)
        self.start_spin_box.setMinimum(minimum)
        self.stop_spin_box.setMaximum(maximum)
        self.stop_spin_box.setMinimum(minimum)

    @asyncSlot(int)
    async def set_relative_position(self, is_relative: int):
        """Adjust the target position based on relative/aboslute mode."""
        self.is_relative = bool(is_relative)
        device = self.motor_box.current_component()
        if device is None:
            return
        params = await device_parameters(device)
        # Get last values first to avoid limit crossing
        widgets = [self.start_spin_box, self.stop_spin_box]
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
        start = self.start_spin_box.value()
        stop = self.stop_spin_box.value()
        precision = max(self.start_spin_box.decimals(), self.stop_spin_box.decimals())
        # Calculate step size
        try:
            step_size = (stop - start) / (self.num_points - 1)
        except (ValueError, ZeroDivisionError):
            self.step_label.setText("nan")
        else:
            step_size = round(step_size, precision)
            self.step_label.setText(str(step_size))


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

    def plan_args(self) -> tuple[tuple, dict]:
        # Get scan parameters from widgets
        detectors = self.ui.detectors_list.selected_detectors()
        # Get parameters from each row of line regions
        device_names = [
            region.motor_box.current_component().name for region in self.regions
        ]
        device_names = [sanitize_name(name) for name in device_names]
        start_points = [region.start_spin_box.value() for region in self.regions]
        stop_points = [region.stop_spin_box.value() for region in self.regions]
        device_args = [
            values
            for entry in zip(device_names, start_points, stop_points)
            for values in entry
        ]
        args = (detectors, *device_args)
        kwargs = {
            "num": self.ui.scan_pts_spin_box.value(),
            "md": self.get_meta_data(),
        }
        return args, kwargs

    @property
    def plan_type(self) -> str:
        """Determine what kind of scan we're running based on use input."""
        return {
            # Rel, log
            (True, True): "rel_log_scan",
            (True, False): "rel_scan",
            (False, True): "log_scan",
            (False, False): "scan",
        }[
            (
                self.ui.relative_scan_checkbox.isChecked(),
                self.ui.log_scan_checkbox.isChecked(),
            )
        ]

    @property
    def scan_repetitions(self) -> int:
        """How many times should each scan be run."""
        return self.ui.spinBox_repeat_scan_num.value()

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
