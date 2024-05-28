import logging

from bluesky_queueserver_api import BPlan
from qtpy import QtWidgets

from firefly import display
from firefly.component_selector import ComponentSelector

log = logging.getLogger(__name__)

# ROBOT_NAMES = ["Austin"]

SAMPLE_NUMBERS = [8, 9, 10, 14, 15, 16, 20, 21, 22, None]  # list(range(24))+[None]


class LineScanRegion:
    def __init__(self):
        self.setup_ui()

    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()

        # First item, motor No.
        # self.motor_label = QtWidgets.QLabel()
        # self.motor_label.setText("1")
        # self.layout.addWidget(self.motor_label)

        # Second item, ComponentSelector
        self.motor_box = ComponentSelector()
        # self.stop_line_edit.setPlaceholderText("Stop…")
        self.layout.addWidget(self.motor_box)

        # Third item, start point
        self.start_line_edit = QtWidgets.QLineEdit()
        self.start_line_edit.setPlaceholderText("Position…")
        self.layout.addWidget(self.start_line_edit)

        # Forth item, stop point
        # self.stop_line_edit = QtWidgets.QLineEdit()
        # self.stop_line_edit.setPlaceholderText("Stop…")
        # self.layout.addWidget(self.stop_line_edit)


class RobotDisplay(display.FireflyDisplay):
    """
    A GUI for managing sample tranfer using a robot plan: robot_sample(robot, number/None, motor1, position1, motor2, position2, motor3, position...)
    """

    def customize_ui(self):
        self.reset_default_regions()
        # disable the line edits in spin box
        # self.ui.robot_combo_box.lineEdit().setReadOnly(True)
        # clear any exiting items in the combo box
        # self.ui.robot_combo_box.clear()
        # set the list of values for the combo box
        # for rbt in ROBOT_NAMES:
        #    self.ui.robot_combo_box.addItem(rbt)

        # clear any exiting items in the combo box
        self.ui.sample_combo_box.clear()
        # set the list of values for the combo box
        for sam in SAMPLE_NUMBERS:
            self.ui.sample_combo_box.addItem(str(sam))
        # self.ui.sample_combo_box.setCurrentIndex(0)

        # disable the line edits in spin box
        self.ui.num_motor_spin_box.lineEdit().setReadOnly(True)
        self.ui.num_motor_spin_box.valueChanged.connect(self.update_regions)
        # self.ui.num_motor_spin_box.editingFinished.connect(self.update_regions)

        # self.ui.run_button.setEnabled(True) #for testing
        self.ui.run_button.clicked.connect(self.queue_plan)

    def reset_default_regions(self):
        default_num_regions = 1
        if not hasattr(self, "regions"):
            self.regions = []
            self.add_regions(default_num_regions)
        self.ui.num_motor_spin_box.setValue(default_num_regions)
        self.update_regions()

    def add_regions(self, num=1):
        for i in range(num):
            region = LineScanRegion()
            self.ui.regions_layout.addLayout(region.layout)
            # Save it to the list
            self.regions.append(region)

    def remove_regions(self, num=1):
        for i in range(num):
            layout = self.regions[-1].layout
            # iterate/wait, and delete all widgets in the layout in the end
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.regions.pop()

    def update_regions(self):
        new_region_num = self.ui.num_motor_spin_box.value()
        old_region_num = len(self.regions)
        diff_region_num = new_region_num - old_region_num

        if diff_region_num < 0:
            self.remove_regions(abs(diff_region_num))
        elif diff_region_num > 0:
            self.add_regions(diff_region_num)

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
        print(args)
        print(sam_num)
        robot = self.macros()["DEVICE"]
        print(robot)
        item = BPlan("robot_transfer_sample", robot, sam_num, *args)

        # Submit the item to the queueserver
        from firefly.application import FireflyApplication

        app = FireflyApplication.instance()
        log.info("Add ``robot_transfer_sample()`` plan to queue.")
        app.add_queue_item(item)

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
