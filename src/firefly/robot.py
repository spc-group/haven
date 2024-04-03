import logging

import bluesky_queueserver_api import BPlan
from qtpy import QtWidgets
from firefly import display
from firefly.application import FireflyApplication
from firefly.component_selector import ComponentSelector

from have import exceptions, load_config, registry

log = logging.getLogger(__name__)

SAMPLE_NUMBERS = range(24)

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
        self.start_line_edit.setPlaceholderText("Start…")
        self.layout.addWidget(self.start_line_edit)

        # Forth item, stop point
        self.stop_line_edit = QtWidgets.QLineEdit()
        self.stop_line_edit.setPlaceholderText("Stop…")
        self.layout.addWidget(self.stop_line_edit)




class RobotDisplay(display.FireflyDisplay):
    """
    A GUI for managing sample tranfer using a robot
    """

    def customize_ui(self):
        # disable the line edits in spin box
        self.ui.num_motor_spin_box.lineEdit().setReadOnly(True)
        self.ui.num_motor_spin_box.valueChanged.connect(self.update_regions)
        # self.ui.num_motor_spin_box.editingFinished.connect(self.update_regions)

        # self.ui.run_button.setEnabled(True) #for testing
        self.ui.run_button.clicked.connect(self.queue_plan)
    
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
        num_readings = self.ui.num_spinbox.value()
        delay = self.ui.delay_spinbox.value()
        detectors = self.ui.detectors_list.selected_detectors()
        # Build the queue item

        item = BPlan("count", delay=delay, num=num_readings, detectors=detectors)
        # Submit the item to the queueserver
        from firefly.application import FireflyApplication

        app = FireflyApplication.instance()
        log.info("Add ``count()`` plan to queue.")
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
