import logging
from typing import Sequence, Mapping, Optional

from pydm.widgets.channel import PyDMChannel
from haven.instrument.ion_chamber import IonChamber
from haven import load_config, exceptions, registry

from firefly import display

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
    gain_values = [1, 2, 5, 10, 20, 50, 100, 200, 500]
    gain_units = ["pA/V", "nA/V", "µA/V", "mA/V"]
    gain = float("nan")
    gain_unit = "A"
    last_voltage = 0

    def __init__(
        self,
        device: IonChamber = None,
        args: Optional[Sequence] = None,
        macros: Mapping = {},
        **kwargs,
    ):
        self._device = device
        super().__init__(macros=macros, args=args, **kwargs)

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
        # Setup a pydm channel to monitor the gain on the pre-amplifier
        self._ch_gain_value = PyDMChannel(
            self.ui.sens_num_label.channel, value_slot=self.update_gain
        )
        self._ch_gain_unit = PyDMChannel(
            self.ui.sens_unit_label.channel, value_slot=self.update_gain_unit
        )
        self._ch_voltage = PyDMChannel(
            self.ui.ion_chamber_label.channel, value_slot=self.update_current
        )
        for ch in [self._ch_voltage, self._ch_gain_value, self._ch_gain_unit]:
            ch.connect()

    def update_gain(self, new_gain_idx):
        self.gain = self.gain_values[new_gain_idx]
        log.debug(f"Updated gain value: {self.gain}")
        self.update_current(self.last_voltage)

    def update_gain_unit(self, new_unit_idx):
        unit = self.gain_units[new_unit_idx]
        self.gain_unit = unit.split("/")[0]
        log.debug(f"Updated gain unit: {self.gain_unit}")
        self.update_current(self.last_voltage)

    def update_current(self, voltage):
        self.last_voltage = voltage
        text = f"({voltage * self.gain:.02f} {self.gain_unit})"
        log.debug(f"New current text: {text}")
        self.ui.ion_chamber_current.setText(text)

    def customize_ui(self):
        # Gain adjustment buttons
        if self._device is not None:
            self.ui.gain_up_button.clicked.connect(self._device.increase_gain)
            self.ui.gain_down_button.clicked.connect(self._device.decrease_gain)
        else:
            log.warning("Cannot attach voltmeter buttons to device.")

    def ui_filename(self):
        return "voltmeter.ui"
