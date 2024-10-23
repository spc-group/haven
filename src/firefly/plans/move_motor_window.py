import logging

from bluesky_queueserver_api import BPlan
from qtpy import QtWidgets
from qtpy.QtGui import QDoubleValidator

from firefly.component_selector import ComponentSelector
from firefly.plans import regions_display

log = logging.getLogger()


class MotorRegion(regions_display.RegionBase):

    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()

        # First item, ComponentSelector
        self.motor_box = ComponentSelector()
        self.layout.addWidget(self.motor_box)

        # Second item, position point
        self.position_line_edit = QtWidgets.QLineEdit()
        self.position_line_edit.setValidator(QDoubleValidator())  # only takes floats
        self.position_line_edit.setPlaceholderText("Position…")
        self.layout.addWidget(self.position_line_edit)


class MoveMotorDisplay(regions_display.RegionsDisplay):
    Region = MotorRegion
    default_num_regions = 1

    def get_scan_parameters(self):
        # get paramters from each rows of line regions:
        motor_lst, position_lst = [], []
        for region_i in self.regions:
            motor_lst.append(region_i.motor_box.current_component().name)
            position_lst.append(float(region_i.position_line_edit.text()))

        motor_args = [
            values for motor_i in zip(motor_lst, position_lst) for values in motor_i
        ]

        return motor_args

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        motor_args = self.get_scan_parameters()

        if self.ui.relative_scan_checkbox.isChecked():
            scan_type = "mvr"
        else:
            scan_type = "mv"

        # # Build the queue item
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
