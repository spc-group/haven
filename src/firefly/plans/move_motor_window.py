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


class MotorRegion(RegionBase):
    default_precision = 5
    is_relative: bool

    def setup_ui(self):
        # ComponentSelector
        self.motor_box = ComponentSelector()
        self.motor_box.device_selected.connect(self.update_device_parameters)

        # Set point
        self.position_spin_box = QtWidgets.QDoubleSpinBox()
        self.position_spin_box.setMaximum(float("inf"))
        self.position_spin_box.setMinimum(float("-inf"))

        self.widgets = [self.motor_box, self.position_spin_box]
        for column, widget in enumerate(self.widgets):
            self.layout.addWidget(widget, self.row, column)

    async def update_devices(self, registry):
        await self.motor_box.update_devices(registry)

    @asyncSlot(Device)
    async def update_device_parameters(self, new_device: Device):
        device = await device_parameters(new_device)
        # Filter out non-numeric datatypes
        self.position_spin_box.setEnabled(device.is_numeric)
        # Set other metadata
        self.set_limits(device)
        self.position_spin_box.setDecimals(device.precision)
        # Handle units
        self.position_spin_box.setSuffix(f" {device.units}")
        # Set starting motor position
        if self.is_relative:
            self.position_spin_box.setValue(0)
        else:
            self.position_spin_box.setValue(device.current_value)

    def set_limits(self, device: DeviceParameters):
        """Set limits on the spin boxes to match the device limits."""
        if self.is_relative:
            minimum = device.minimum - device.current_value
            maximum = device.maximum - device.current_value
        else:
            maximum, minimum = device.maximum, device.minimum
        self.position_spin_box.setMaximum(maximum)
        self.position_spin_box.setMinimum(minimum)

    @asyncSlot(int)
    async def set_relative_position(self, is_relative: int):
        """Adjust the target position based on relative/aboslute mode."""
        self.is_relative = bool(is_relative)
        device = self.motor_box.current_component()
        if device is None:
            return
        params = await device_parameters(device)
        if is_relative:
            new_position = self.position_spin_box.value() - params.current_value
        else:
            new_position = self.position_spin_box.value() + params.current_value
        self.position_spin_box.setValue(new_position)
        self.set_limits(params)


class MoveMotorDisplay(RegionsDisplay):
    Region = MotorRegion
    default_num_regions = 1

    def get_scan_parameters(self):
        # get paramters from each rows of line regions:
        motor_lst, position_lst = [], []
        for region_i in self.regions:
            motor_lst.append(region_i.motor_box.current_component().name)
            position_lst.append(region_i.position_spin_box.value())

        motor_args = [
            values for motor_i in zip(motor_lst, position_lst) for values in motor_i
        ]

        return motor_args

    def add_region(self):
        new_region = super().add_region()
        self.relative_scan_checkbox.stateChanged.connect(
            new_region.set_relative_position
        )
        new_region.set_relative_position(self.relative_scan_checkbox.checkState())
        return new_region

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        motor_args = self.get_scan_parameters()

        if self.ui.relative_scan_checkbox.isChecked():
            scan_type = "mvr"
        else:
            scan_type = "mv"

        # Build the queue item
        item = BPlan(
            scan_type,
            *motor_args,
        )

        # Submit the item to the queueserver
        log.info("Added line scan() plan to queue.")
        self.queue_item_submitted.emit(item)

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
