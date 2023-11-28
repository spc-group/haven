import logging
from typing import Mapping, Optional, Sequence

import qtawesome as qta

from firefly import FireflyApplication, display
from haven import exceptions, registry
from haven.instrument.ion_chamber import IonChamber

log = logging.getLogger(__name__)


class VoltmeterDisplay(display.FireflyDisplay):
    """PyDM display for showing a single voltmeter.

    Parameters
    ==========
    device
      An ophyd Device object for the ion chamber. If ``None``, then
      the device will be retrieved from the haven instrument registry
      based on its name in *macros["IC"]*.
    args
      Additional argument passed to the parent display class.
    macros
      Macros used to build the display (described below).

    Macros
    ======
    IC
      The name of the ophyd device describing the ion chamber
      associated with this voltmeter. The Device object itself will be
      retrieved from the haven registry if *device* is ``None``
      (default).

    """

    _device: IonChamber = None

    def __init__(
        self,
        device: IonChamber = None,
        args: Optional[Sequence] = None,
        macros: Mapping = {},
        **kwargs,
    ):
        self._device = device
        super().__init__(macros=macros, args=args, **kwargs)

    def customize_ui(self):
        # Wire up the "settings" button the ion chamber's config window
        app = FireflyApplication.instance()
        ic_action = app.ion_chamber_actions[self._device.name]
        self.ui.settings_button.clicked.connect(ic_action.trigger)
        self.ui.settings_button.setIcon(qta.icon("fa5s.cog"))
        # Use qtawesome icons instead of unicode arrows
        self.ui.gain_down_button.setText("")
        self.ui.gain_down_button.setIcon(qta.icon("fa5s.arrow-left"))
        self.ui.gain_up_button.setText("")
        self.ui.gain_up_button.setIcon(qta.icon("fa5s.arrow-right"))

    def customize_device(self):
        # Find and store the hardware device
        device_name = self.macros().get("IC")
        if self._device is None:
            try:
                self._device = registry.find(name=device_name)
            except exceptions.ComponentNotFound:
                log.warning(f"No device loaded for voltmeter: {self.macros()}.")
            else:
                log.debug(f"Voltmeter found device: {self._device}")

    def ui_filename(self):
        return "voltmeter.ui"


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
