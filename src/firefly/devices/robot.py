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

log = logging.getLogger(__name__)


class RobotMotorRegion(RegionBase):
    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()

        # ComponentSelector
        self.motor_box = ComponentSelector()
        self.layout.addWidget(self.motor_box)

        # Motor position for robot transferring samples
        self.position_spin_box = QtWidgets.QDoubleSpinBox()
        self.position_spin_box.setMinimum(float("-inf"))
        self.position_spin_box.setMaximum(float("inf"))
        self.layout.addWidget(self.position_spin_box)

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
        self.position_spin_box.setValue(device.current_value)

    def set_limits(self, device: DeviceParameters):
        """Set limits on the spin boxes to match the device limits."""
        maximum, minimum = device.maximum, device.minimum
        self.position_spin_box.setMaximum(maximum)
        self.position_spin_box.setMinimum(minimum)


class RobotDisplay(RegionsDisplay):
    """Manage sample transfer using a robot plan.

    .. code-block:: python

      robot_sample(robot, number/None, motor1, position1, motor2,
                   position2, motor3, position3, …)

    """

    Region = RobotMotorRegion
    plan_type = "robot_transfer_sample"
    default_num_regions = 0

    def sample_numbers(self):
        sample_names = [name for name, device in self.device.samples.walk_subdevices()]
        sample_numbers = [int(name.replace("sample", "")) for name in sample_names]
        sample_numbers.append(None)
        return sample_numbers

    def customize_ui(self):
        super().customize_ui()
        # set the list of values for the combo box
        self.ui.sample_combo_box.clear()
        for sam in self.sample_numbers():
            self.ui.sample_combo_box.addItem(str(sam))

    def plan_args(self):
        # Get the sample number from the sample_spin_box
        sam_num_str = self.ui.sample_combo_box.currentText()
        # Convert sam_num_str to an integer if it's a string representation of a number
        sam_num = int(sam_num_str) if sam_num_str.isdigit() else None
        # Get parameters from device regions
        devices = [region.motor_box.current_component() for region in self.regions]
        device_names = [sanitize_name(device.name) for device in devices]
        positions = [float(region.position_spin_box.text()) for region in self.regions]
        position_args = [
            values for region in zip(device_names, positions) for values in region
        ]
        # Build the arguments
        robot = self.macros()["DEVICE"]
        args = (robot, sam_num, *position_args)
        kwargs = {}
        return args, kwargs

    def ui_filename(self):
        return "devices/robot.ui"


# -----------------------------------------------------------------------------
# :author:    Yanna Chen
# :email:     yannachen@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full licens is in the file LICENSE, distributed with this software.
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
