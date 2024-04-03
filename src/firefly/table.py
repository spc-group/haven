import warnings
from pathlib import Path
from typing import Mapping

import haven
from firefly import display
from haven.instrument import Table


class CaQtDMBase:
    """caQtDM parameters for the given table.

    Different table geometries require different caQtDM
    configurations.

    """

    ui_file: str = ""
    macros: Mapping = {}
    table: Table

    def __init__(self, table: Table):
        self.table = table

    def motor_attrs(self):
        attr_names = ["horizontal", "vertical"]
        # Look for which motor is present on this table device
        attrs = []
        for attr in attr_names:
            if getattr(self.table, attr, None) is not None:
                attrs.append(attr)
        return attrs


class TwoLegCaQtDM(CaQtDMBase):
    """caQtDM parameters for a table with two ."""

    ui_file = "/net/s25data/xorApps/ui/table_2leg.ui"

    @property
    def macros(self):
        macros = {
            "PM": self.table.prefix,
            "TB": self.table.pseudo_motors.strip(":"),
            "TR": self.table.transforms.strip(":"),
            "TBUS": self.table.__class__.upstream.suffix,
            "TBDS": self.table.__class__.downstream.suffix,
        }
        # See if there's a horizontal motor
        horizontal = getattr(self.table.__class__, "horizontal", None)
        if horizontal is not None:
            macros["TBH"] = horizontal.suffix
        return macros


class SingleMotorCaQtDM(CaQtDMBase):
    """caQtDM parameters for a table with only a single motor."""

    ui_file = "/APSshare/epics/synApps_6_2_1/support/motor-R7-2-2//motorApp/op/ui/autoconvert/motorx.ui"

    @property
    def macros(self):
        # Look for which motor is present on this table device
        for attr in self.motor_attrs():
            component = getattr(self.table.__class__, attr)
            return {"M": component.suffix}
        raise RuntimeError(f"Could not find single motor for {self.device}.")


class MultipleMotorCaQtDM(CaQtDMBase):
    """caQtDM parameters for a table with only multiple independent motors."""

    @property
    def ui_file(self):
        ui_dir = Path(
            "/APSshare/epics/synApps_6_2_1/support/motor-R7-2-2//motorApp/op/ui/autoconvert/"
        )
        num_motors = len(self.motor_attrs())
        ui_path = ui_dir / f"motor{num_motors}x.ui"
        return str(ui_path)

    @property
    def macros(self):
        # Look for which motor is present on this table device
        macros = {}
        for idx, name in enumerate(self.motor_attrs()):
            component = getattr(self.table.__class__, name)
            key = f"M{idx+1}"
            macros[key] = component.suffix
        return macros


class TableDisplay(display.FireflyDisplay):
    def customize_device(self):
        self.device = haven.registry.find(self.macros()["DEVICE"])
        # Determine which flavor of caQtDM parameters we need
        if self.num_legs == 2:
            self.caqtdm = TwoLegCaQtDM(table=self.device)
        elif self.num_motors == 1:
            self.caqtdm = SingleMotorCaQtDM(table=self.device)
        elif self.num_motors > 1:
            self.caqtdm = MultipleMotorCaQtDM(table=self.device)
        else:
            warnings.warn(
                f"Could not determine caQtDM parameters for device: {self.device}."
            )
            self.caqtdm = CaQtDMBase(table=self.device)

    def ui_filename(self):
        return "table.ui"

    @property
    def caqtdm_ui_file(self):
        return self.caqtdm.ui_file

    @property
    def num_legs(self):
        """How motorized legs does this table have?

        If 1, it's a simple motorized table. If greater than 1, it
        will probably have some angular control over the table
        surface.

        """
        leg_names = {"upstream", "downstream"}
        num_legs = len(list(set(self.device.component_names) & leg_names))
        return num_legs

    @property
    def num_motors(self):
        """How many motors does this table have?

        Does not include the pseudo motors produce through the
        sum2Diff EPICS record.

        """
        motor_names = {"horizontal", "vertical", "upstream", "downstream"}
        num_motors = len(list(set(self.device.component_names) & motor_names))
        return num_motors

    def customize_ui(self):
        # Disable motor controls if the given axis is not available
        self.ui.pitch_embedded_display.setEnabled(hasattr(self.device, "pitch"))
        self.ui.vertical_embedded_display.setEnabled(hasattr(self.device, "vertical"))
        self.ui.horizontal_embedded_display.setEnabled(
            hasattr(self.device, "horizontal")
        )

    def launch_caqtdm(self):
        # Sort out the prefix from the slit designator
        prefix = self.device.prefix.strip(":")
        pieces = prefix.split(":")
        # Build the macros for the caQtDM panels
        P = ":".join(pieces[:-1])
        caqtdm_macros = dict(
            P=self.device.prefix,
            **self.caqtdm.macros,
        )
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
