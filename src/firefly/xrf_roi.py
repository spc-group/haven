import qtawesome as qta
from qtpy.QtCore import Signal

from firefly import display


class XRFROIDisplay(display.FireflyDisplay):
    enabled_background = "rgb(212, 237, 218)"  # Pale green
    selected_background = "rgb(204, 229, 255)"  # Pale blue

    # Signals
    selected = Signal(bool)

    def ui_filename(self):
        return "xrf_roi.ui"

    def customize_ui(self):
        self.ui.set_roi_button.setIcon(qta.icon("fa5s.chart-line"))
        self.ui.enabled_checkbox.toggled.connect(self.set_backgrounds)
        self.ui.set_roi_button.toggled.connect(self.set_backgrounds)
        self.ui.enabled_checkbox.toggled.connect(self.enable_roi)
        self.ui.set_roi_button.toggled.connect(self.selected)

    def set_backgrounds(self):
        is_selected = self.ui.set_roi_button.isChecked()
        if is_selected:
            self.setStyleSheet(f"background: {self.selected_background}")
        else:
            self.setStyleSheet("")

    def enable_roi(self, is_enabled):
        if not is_enabled:
            # Unselect this channel so we don't get locked out
            self.ui.set_roi_button.setChecked(False)


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
