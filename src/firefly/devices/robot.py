import logging

from firefly.plans import display
from firefly.plans.move import MotorRegionsManager

log = logging.getLogger(__name__)


class RobotDisplay(display.PlanDisplay):
    """Manage sample transfer using a robot plan.

    .. code-block:: python

      robot_sample(robot, number/None, motor1, position1, motor2,
                   position2, motor3, position3, …)

    """

    plan_type = "robot_transfer_sample"
    default_num_regions = 0

    def sample_numbers(self):
        return [*self.device.samples.keys(), None]

    def customize_ui(self):
        super().customize_ui()
        self.regions = MotorRegionsManager(layout=self.regions_layout)
        self.regions.is_relative = False
        self.enable_all_checkbox.stateChanged.connect(self.regions.enable_all_rows)
        # set the list of values for the combo box
        self.ui.sample_combo_box.clear()
        for sam in self.sample_numbers():
            self.ui.sample_combo_box.addItem(str(sam))

    def plan_args(self) -> tuple[tuple, dict]:
        # Get the sample number from the sample_spin_box
        sam_num_str = self.ui.sample_combo_box.currentText()
        # Convert sam_num_str to an integer if it's a string representation of a number
        sam_num = int(sam_num_str) if sam_num_str.isdigit() else None
        # Get parameters from device regions
        region_args = [(region.device, region.position) for region in self.regions]
        position_args = tuple(arg for region in region_args for arg in region)
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
