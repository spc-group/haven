import logging
from typing import Sequence, Mapping, Optional

from pydm.widgets.channel import PyDMChannel
from haven.instrument.ion_chamber import IonChamber
from haven import load_config, exceptions, registry
import qtawesome as qta

from firefly import display, FireflyApplication

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
