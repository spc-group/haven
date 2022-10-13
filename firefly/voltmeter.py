import logging

from haven.instrument.ion_chamber import IonChamber, pv_prefix

from firefly import display

log = logging.getLogger(__name__)


class VoltmeterDisplay(display.FireflyDisplay):
    _device: IonChamber = None
    
    def __init__(self, device: IonChamber=None, args=None, macros={}, **kwargs):
        self._device = device
        super().__init__(macros=macros, args=args, **kwargs)
    
    def customize_device(self):
        # Create and store the hardware device
        ch_num = self.macros().get("CHANNEL_NUMBER", None)
        if self._device is None:
            if ch_num is not None:
                # Create a new device
                self._device = IonChamber(ch_num=ch_num, prefix=pv_prefix, name=f"ion chamber {ch_num}")
                log.debug(f"Voltmeter created new device: {self._device}")
            else:
                log.warning(f"No device loaded for voltmeter: {macros}.")
    
    def customize_ui(self):
        # Gain adjustment buttons
        if self._device is not None:
            self.ui.gain_up_button.clicked.connect(self._device.increase_gain)
            self.ui.gain_down_button.clicked.connect(self._device.decrease_gain)
        else:
            log.warning("Cannot attach voltmeter buttons to device.")
    
    def ui_filename(self):
        return "voltmeter.ui"
