from firefly import slits
from haven.instrument import mirrors


class MirrorDisplay(slits.SlitsDisplay):
    caqtdm_ui_filenames = {
        mirrors.HighHeatLoadMirror: "/net/s25data/xorApps/epics/synApps_6_2/ioc/25ida/25idaApp/op/ui/HHLM_4.ui",
        mirrors.BendableHighHeatLoadMirror: "/net/s25data/xorApps/epics/synApps_6_2/ioc/25ida/25idaApp/op/ui/HHLM_6.ui",
    }

    def customize_ui(self):
        # Enable the bender controls if the mirror is bendable
        if self.device.bendable:
            self.ui.bender_embedded_display.setEnabled(True)

    def ui_filename(self):
        return "mirror.ui"

    def launch_caqtdm(self):
        # Sort out the prefix from the slit designator
        prefix = self.device.prefix.strip(":")
        pieces = prefix.split(":")
        # Build the macros for the caQtDM panels
        P = ":".join(pieces[:-1])
        caqtdm_macros = {
            "P": f"{P}:",
            "MIR": f"{pieces[-1]}:",
            "Y": self.device.transverse.prefix.split(":")[-1],
            "ROLL": self.device.roll.prefix.split(":")[-1],
            "LAT": self.device.normal.prefix.split(":")[-1],
            "CP": self.device.pitch.prefix.split(":")[-1],
            "UPL": self.device.upstream.prefix.split(":")[-1],
            "DNL": self.device.downstream.prefix.split(":")[-1],
        }
        if self.device.bendable:
            caqtdm_macros["BEND"] = self.device.bender.prefix.split(":")[-1]
        # Launch the caQtDM panel
        super(slits.SlitsDisplay, self).launch_caqtdm(macros=caqtdm_macros)


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
