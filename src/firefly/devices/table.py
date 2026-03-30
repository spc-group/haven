import logging

from firefly import display
from haven import beamline

log = logging.getLogger(__name__)


class TableDisplay(display.FireflyDisplay):
    def customize_device(self):
        self.device = beamline.devices[self.macros()["DEVICE"]]

    def ui_filename(self):
        return "devices/table.ui"

    @property
    def num_legs(self):
        """How motorized legs does this table have?

        If 1, it's a simple motorized table. If greater than 1, it
        will probably have some angular control over the table
        surface.

        """
        leg_names = {"upstream", "downstream"}
        num_legs = len([name for name in leg_names if hasattr(self.device, name)])
        return num_legs

    @property
    def num_motors(self):
        """How many motors does this table have?

        Does not include the pseudo motors produce through the
        sum2Diff EPICS record.

        """
        motor_names = {"horizontal", "vertical", "upstream", "downstream"}
        num_motors = len([name for name in motor_names if hasattr(self.device, name)])
        return num_motors

    def customize_ui(self):
        # Disable motor controls if the given axis is not available
        self.ui.pitch_embedded_display.setEnabled(hasattr(self.device, "pitch"))
        self.ui.vertical_embedded_display.setEnabled(hasattr(self.device, "vertical"))
        self.ui.horizontal_embedded_display.setEnabled(
            hasattr(self.device, "horizontal")
        )


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
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
