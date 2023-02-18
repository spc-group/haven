import logging

from pydm.widgets.channel import PyDMChannel
from haven.instrument.ion_chamber import IonChamber
from haven import load_config

from firefly import display

log = logging.getLogger(__name__)


class VoltmeterDisplay(display.FireflyDisplay):
    _device: IonChamber = None
    gain_values = [1, 2, 5, 10, 20, 50, 100, 200, 500]
    gain_units = ["pA/V", "nA/V", "µA/V", "mA/V"]
    
    def __init__(self, device: IonChamber = None, args=None, macros={}, **kwargs):
        self._device = device
        default_ioc_prefix = load_config()['ion_chamber']['scaler']['ioc']
        macros['IOC_VME'] = macros.get("IOC_VME", default_ioc_prefix)
        super().__init__(macros=macros, args=args, **kwargs)
    
    def customize_device(self):
        # Create and store the hardware device
        ch_num = self.macros().get("CHANNEL_NUMBER", None)
        config = load_config()
        # preamp_ioc = config["ion_chamber"]["preamp"]["ioc"]
        preamp_prefix = self.macros().get("PREAMP_PREFIX", "")
        scaler_prefix = self.macros().get("SCALER_PREFIX", "")
        # preamp_prefix = f"{preamp_ioc}:{record}"
        if self._device is None:
            if ch_num is not None:
                # Create a new device
                self._device = IonChamber(ch_num=ch_num, prefix=scaler_prefix, preamp_prefix=preamp_prefix, name=f"ion chamber {ch_num}")
                log.debug(f"Voltmeter created new device: {self._device}")
            else:
                log.warning(f"No device loaded for voltmeter: {self.macros}.")
        # Setup a pydm channel to monitor the gain on the pre-amplifier
        self._ch_gain_value = PyDMChannel("", value_slot=self.update_gain)
        self._ch_gain_unit = PyDMChannel("", value_slot=self.update_gain_unit)
        self._ch_voltage = PyDMChannel(self.ui.ion_chamber_label.channel, value_slot=self.update_current)

    def update_gain(self, new_gain_idx):
        self.gain = self.gain_values[new_gain_idx]

    def update_gain_unit(self, new_unit_idx):
        unit = self.gain_units[new_unit_idx]
        self.gain_unit = unit.split("/")[0]

    def update_current(self, voltage):
        text = f"({voltage / self.gain} {self.gain_unit})"
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
