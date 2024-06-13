import logging
import warnings

import haven
from firefly import display
from haven.instrument import slits

log = logging.getLogger(__name__)


class SlitsDisplay(display.FireflyDisplay):
    caqtdm_ui_filenames = {
        slits.BladeSlits: "/APSshare/epics/synApps_6_2_1/support/optics-R2-13-5//opticsApp/op/ui/autoconvert/4slitGraphic.ui",
        slits.ApertureSlits: "/net/s25data/xorApps/epics/synApps_6_2/ioc/25ida/25idaApp/op/ui/maskApertureSlit.ui",
    }

    def customize_device(self):
        self.device = haven.registry.find(self.macros()["DEVICE"])

    def ui_filename(self):
        return "slits.ui"

    @property
    def caqtdm_ui_file(self):
        # Go up the class list until we find a class that is recognized
        for Cls in self.device.__class__.__mro__:
            try:
                return self.caqtdm_ui_filenames[Cls]
            except KeyError:
                continue
        # We didn't find any supported classes of slits
        msg = (
            "Could not find caQtDM filename for optic "
            f"{self.device.name} ({self.device.__class__})."
        )
        warnings.warn(msg)
        log.warning(msg)
        return ""

    def launch_caqtdm(self):
        # Sort out the prefix from the slit designator
        prefix = self.device.prefix.strip(":")
        pieces = prefix.split(":")
        # Build the macros for the caQtDM panels
        P = ":".join(pieces[:-1])
        SLIT = ":".join(pieces[-1:])
        H = self.device.h.prefix.split(":")[1]
        V = self.device.v.prefix.split(":")[1]
        caqtdm_macros = {
            "P": f"{P}:",
            # For 4-blade slits
            "SLIT": SLIT,
            "H": H,
            "V": V,
            # For rotary aperture slits
            "SLITS": SLIT,
        }
        # Add extra motors if applicable
        motors = {
            "HOR": "horizontal",
            "DIAG": "diagonal",
            "YAW": "yaw",
            "PITCH": "pitch",
        }
        for key, attr in motors.items():
            if not hasattr(self.device, attr):
                continue
            # Get the motor number from the device
            suffix = getattr(self.device, attr).prefix.split(":")[-1]
            caqtdm_macros[key] = suffix
        # Launch the caQtDM panel
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
