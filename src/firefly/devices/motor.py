import qtawesome as qta

import haven
from firefly import display


class MotorDisplay(display.FireflyDisplay):
    caqtdm_ui_file = "/APSshare/epics/synApps_6_2_1/support/motor-R7-2-2/motorApp/op/ui/autoconvert/motorx_all.ui"

    def customize_ui(self):
        super().customize_ui()
        self.ui.stop_button.setIcon(qta.icon("fa6s.stop"))

    def ui_filename(self):
        return "devices/motor.ui"

    def launch_caqtdm(self):
        device = haven.registry.find(self.macros()["MOTOR"])
        P, M = device.prefix.split(":")[0:2]
        caqtdm_macros = {
            "P": f"{P}:",
            "M": M,
        }
        super().launch_caqtdm(macros=caqtdm_macros)


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
