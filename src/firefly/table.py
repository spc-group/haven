import logging
import warnings
from pathlib import Path

from firefly import display
from haven import beamline, load_config
from haven.devices import Table

log = logging.getLogger(__name__)


class CaQtDMBase:
    """caQtDM parameters for the given table.

    Different table geometries require different caQtDM
    configurations.

    """

    ui_file: str = ""
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

    @property
    def macros(self):
        # See if the Haven config file has the caQtDM macro string
        config = load_config()
        try:
            macro_str = config["table"][self.table.name]["caqtdm_macros"]
        except KeyError:
            log.warning(f"No caQtDM macro string for table: {self.table.name}")
            return {}
        # Parse out the caQtDM string
        macros = {
            k: v for k, v in (piece.split("=", 1) for piece in macro_str.split(","))
        }
        return macros


class TwoLegCaQtDM(CaQtDMBase):
    """caQtDM parameters for a table with two ."""

    ui_file = "/net/s25data/xorApps/ui/table_2leg.ui"


def parse_motor_source(motor):
    source = motor.user_readback.source
    transport, pv = source.split("://", maxsplit=1)
    prefix, suffix = pv.removesuffix(".RBV").rsplit(":", maxsplit=1)
    return transport, prefix, suffix


class SingleMotorCaQtDM(CaQtDMBase):
    """caQtDM parameters for a table with only a single motor."""

    ui_file = "/APSshare/epics/synApps_6_2_1/support/motor-R7-2-2//motorApp/op/ui/autoconvert/motorx.ui"


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


class TableDisplay(display.FireflyDisplay):
    def customize_device(self):
        self.device = beamline.devices[self.macros()["DEVICE"]]
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

    def launch_caqtdm(self):
        # Build the macros for the caQtDM panels
        caqtdm_macros = dict(
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
