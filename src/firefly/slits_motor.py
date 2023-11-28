import qtawesome as qta

from firefly import display


class SlitsMotorDisplay(display.FireflyDisplay):
    def customize_ui(self):
        # Make the tweak buttons use proper arrow icons
        title = self.macros()["TITLE"]
        if "Size" in title:
            forward_icon = qta.icon("fa5s.plus")
            reverse_icon = qta.icon("fa5s.minus")
        elif "Vertical Center" in title:
            forward_icon = qta.icon("fa5s.arrow-up")
            reverse_icon = qta.icon("fa5s.arrow-down")
        else:
            forward_icon = qta.icon("fa5s.arrow-right")
            reverse_icon = qta.icon("fa5s.arrow-left")
        self.ui.tweak_forward_button.setIcon(forward_icon)
        self.ui.tweak_reverse_button.setIcon(reverse_icon)
        for btn in [self.ui.tweak_reverse_button, self.ui.tweak_forward_button]:
            btn.setText("")

    def ui_filename(self):
        return "slits_motor.ui"


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
