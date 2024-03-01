import qtawesome as qta
from qtpy import QtWidgets

from firefly import display
from haven import registry


class IonChamberDisplay(display.FireflyDisplay):
    """A GUI window for changing settings in an ion chamber."""

    caqtdm_scaler_ui_file: str = "/net/s25data/xorApps/ui/scaler32_full_offset.ui"
    caqtdm_mcs_ui_file: str = (
        "/APSshare/epics/synApps_6_2_1/support/mca-R7-9//mcaApp/op/ui/autoconvert/SIS38XX.ui"
    )
    caqtdm_preamp_ui_file: str = (
        "/net/s25data/xorApps/epics/synApps_6_2_1/support/ip-GIT/ipApp/op/ui/autoconvert/SR570.ui"
    )

    def customize_device(self):
        self._device = registry.find(self.macros()["IC"])

    def customize_ui(self):
        # Use qtawesome icons instead of unicode arrows
        self.ui.gain_down_button.setText("")
        self.ui.gain_down_button.setIcon(qta.icon("fa5s.arrow-left"))
        self.ui.gain_up_button.setText("")
        self.ui.gain_up_button.setIcon(qta.icon("fa5s.arrow-right"))

    def ui_filename(self):
        return "ion_chamber.ui"

    def prepare_caqtdm_actions(self):
        self.caqtdm_actions = []
        # Create an action for launching the scaler caQtDM file
        action = QtWidgets.QAction(self)
        action.setObjectName("launch_scaler_caqtdm_action")
        action.setText("&Scaler caQtDM")
        action.triggered.connect(self.launch_scaler_caqtdm)
        action.setIcon(qta.icon("fa5s.wrench"))
        action.setToolTip("Launch the caQtDM panel for the scaler.")
        self.caqtdm_actions.append(action)
        # Create an action for launching the MCS caQtDM file
        action = QtWidgets.QAction(self)
        action.setObjectName("launch_mcs_caqtdm_action")
        action.setText("&MCS caQtDM")
        action.triggered.connect(self.launch_mcs_caqtdm)
        action.setIcon(qta.icon("fa5s.wrench"))
        action.setToolTip(
            "Launch the caQtDM panel for the multi-channel scaler controls."
        )
        self.caqtdm_actions.append(action)
        # Create an action for launching the Preamp caQtDM file
        action = QtWidgets.QAction(self)
        action.setObjectName("launch_preamp_caqtdm_action")
        action.setText("&Preamp caQtDM")
        action.triggered.connect(self.launch_preamp_caqtdm)
        action.setIcon(qta.icon("fa5s.wrench"))
        action.setToolTip("Launch the caQtDM panel for the preamplifier.")
        self.caqtdm_actions.append(action)

    def launch_scaler_caqtdm(self):
        device = self._device
        caqtdm_macros = {
            "P": f"{device.scaler_prefix}:",
            "S": "scaler1",
        }
        return self.launch_caqtdm(
            macros=caqtdm_macros, ui_file=self.caqtdm_scaler_ui_file
        )

    def launch_mcs_caqtdm(self):
        device = self._device
        caqtdm_macros = {
            "P": f"{device.scaler_prefix}:",
        }
        return self.launch_caqtdm(macros=caqtdm_macros, ui_file=self.caqtdm_mcs_ui_file)

    def launch_preamp_caqtdm(self):
        device = self._device
        sep = ":"
        bits = device.preamp_prefix.strip(sep).split(sep)
        prefix = sep.join(bits[:-1])
        amp_suffix = bits[-1]
        caqtdm_macros = {
            "P": f"{prefix}:",
            "A": f"{amp_suffix}:",
        }
        return self.launch_caqtdm(
            macros=caqtdm_macros, ui_file=self.caqtdm_preamp_ui_file
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
