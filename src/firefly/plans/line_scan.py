import logging
from dataclasses import dataclass
from functools import partial

from ophyd_async.core import Device
from qasync import asyncSlot
from qtpy.QtWidgets import QWidget, QDoubleSpinBox, QLabel, QCheckBox

from firefly.component_selector import ComponentSelector
from firefly.plans.regions import (
    DeviceParameters,
    RegionsManager,
    make_relative,
    update_device_parameters
)
from firefly.plans.plan_display import PlanDisplay
from haven import sanitize_name

log = logging.getLogger()


class LineRegionsManager(RegionsManager):
    is_relative: bool

    @dataclass(frozen=True)
    class WidgetSet():
        active_checkbox: QCheckBox
        device_selector: ComponentSelector
        start_spin_box: QDoubleSpinBox
        stop_spin_box: QDoubleSpinBox
        step_label: QLabel

    @dataclass(frozen=True, eq=True)
    class Region():
        is_active: bool
        device: str
        start: float
        stop: float

    def widgets_to_region(self, widgets: WidgetSet) -> Region:
        """Take a list of widgets in a row, and build a Region object.

        """
        device_name = widgets.device_selector.current_device_name()
        return self.Region(
            is_active=widgets.active_checkbox.isChecked(),
            device=sanitize_name(device_name),
            start=widgets.start_spin_box.value(),
            stop=widgets.stop_spin_box.value(),
        )

    async def create_row_widgets(self, row: int) -> list[QWidget]:
        # Component selector
        device_selector = ComponentSelector()
        device_selector.device_selected.connect(partial(self.update_device_parameters, row=row))
        # start point
        start_spin_box = QDoubleSpinBox()
        start_spin_box.lineEdit().setPlaceholderText("Start…")
        start_spin_box.setMinimum(float("-inf"))
        start_spin_box.setMaximum(float("inf"))

        # Stop point
        stop_spin_box = QDoubleSpinBox()
        stop_spin_box.lineEdit().setPlaceholderText("Stop…")
        stop_spin_box.setMinimum(float("-inf"))
        stop_spin_box.setMaximum(float("inf"))

        # Step size (non-editable)
        step_label = QLabel()
        step_label.setText("nan")

        # Connect signals
        update_step_size = self.update_step_size
        start_spin_box.valueChanged.connect(update_step_size)
        stop_spin_box.valueChanged.connect(update_step_size)

        # Add widgets to the layout
        return [
            device_selector,
            start_spin_box,
            stop_spin_box,
            step_label,
        ]

    async def update_devices(self, registry):
        await self.motor_box.update_devices(registry)

    @asyncSlot(Device)
    async def update_device_parameters(self, device: Device, row: int):
        widgets = self.row_widgets(row=row)
        await update_device_parameters(
            device=device,
            widgets=[widgets.start_spin_box, widgets.stop_spin_box],
            is_relative=self.is_relative
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
                widgets=[widgets.start_spin_box, widgets.stop_spin_box],
                is_relative=is_relative,
            )

    def set_num_points(self, num_points):
        self.num_points = num_points
        self.update_step_size()

    def update_step_size(self):
        for row in self.row_numbers:
            widgets = self.row_widgets(row)
            # Get Start and Stop values
            start = widgets.start_spin_box.value()
            stop = widgets.stop_spin_box.value()
            precision = max(widgets.start_spin_box.decimals(), widgets.stop_spin_box.decimals())
            # Calculate step size
            try:
                step_size = (stop - start) / (self.num_points - 1)
            except (ValueError, ZeroDivisionError):
                widgets.step_label.setText("nan")
            else:
                step_size = round(step_size, precision)
                widgets.step_label.setText(str(step_size))


class LineScanDisplay(PlanDisplay):

    def customize_ui(self):
        super().customize_ui()
        self.regions = LineRegionsManager(layout=self.regions_layout, is_relative=self.relative_scan_checkbox.isChecked())
        # Connect signals for total time updates
        self.ui.scan_pts_spin_box.valueChanged.connect(self.update_total_time)
        self.ui.detectors_list.selectionModel().selectionChanged.connect(
            self.update_total_time
        )
        self.ui.scan_pts_spin_box.valueChanged.connect(self.regions.set_num_points)
        self.regions.set_num_points(self.scan_pts_spin_box.value())
        self.ui.spinBox_repeat_scan_num.valueChanged.connect(self.update_total_time)
        self.scan_time_changed.connect(self.scan_duration_label.set_seconds)
        self.total_time_changed.connect(self.total_duration_label.set_seconds)

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

    def plan_args(self) -> tuple[tuple, dict]:
        # Get scan parameters from widgets
        detectors = self.ui.detectors_list.selected_detectors()
        detector_names = [detector.name for detector in detectors]
        # Get parameters from each row of line regions
        region_args = [
            (region.device, region.start, region.stop)
            for region in self.regions
        ]
        device_args = [arg for region in region_args for arg in region]
        args = (detector_names, *device_args)
        kwargs = {
            "num": self.ui.scan_pts_spin_box.value(),
            "md": self.plan_metadata(),
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
