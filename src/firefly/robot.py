import logging

from bluesky_queueserver_api import BPlan
from qtpy import QtWidgets

from firefly.component_selector import ComponentSelector
from firefly.plans import regions_display  # import RegionBase, RegionsDisplay

log = logging.getLogger(__name__)


class RobotMotorRegion(regions_display.RegionBase):
    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()

        # ComponentSelector
        self.motor_box = ComponentSelector()
        self.layout.addWidget(self.motor_box)

        # Motor position for robot transferring samples
        self.start_line_edit = QtWidgets.QLineEdit()
        self.start_line_edit.setPlaceholderText("Position…")
        self.layout.addWidget(self.start_line_edit)


class RobotDisplay(regions_display.RegionsDisplay):
    """Manage sample transfer using a robot plan.

    .. code-block:: python

      robot_sample(robot, number/None, motor1, position1, motor2,
                   position2, motor3, position3, …)

    """

    Region = RobotMotorRegion
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

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        # Get scan parameters from widgets
        num_motor = self.ui.num_motor_spin_box.value()

        # Get the sample number from the sample_spin_box
        sam_num_str = self.ui.sample_combo_box.currentText()
        # Convert sam_num_str to an integer if it's a string representation of a number
        sam_num = int(sam_num_str) if sam_num_str.isdigit() else None

        # get parameters from motor regions
        motor_lst, position_lst = [], []
        for region_i in self.regions:
            motor_lst.append(region_i.motor_box.current_component().name)
            position_lst.append(float(region_i.start_line_edit.text()))

        args = [
            values for motor_i in zip(motor_lst, position_lst) for values in motor_i
        ]

        # Build the queue item
        robot = self.macros()["DEVICE"]
        item = BPlan("robot_transfer_sample", robot, sam_num, *args)

        # Submit the item to the queueserver
        log.info("Add ``robot_transfer_sample()`` plan to queue.")
        self.queue_item_submitted.emit(item)

    def ui_filename(self):
        return "robot.ui"


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
