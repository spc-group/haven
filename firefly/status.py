import haven

from firefly import display


class StatusDisplay(display.FireflyDisplay):

    def __init__(self, args=None, macros={}, **kwargs):
        # Get the devices that we need
        shutterA = haven.registry.find(name="Shutter A")
        shutters = haven.registry.findall(label="shutters")
        try:
            shutterCD = [s for s in shutters if s.name != "Shutter A"][0]
        except IndexError:
            # We only have one shutter, probably during testing
            # so for now we just reuse the A shutter.
            shutterCD = shutterA
        mono = haven.registry.find(name="monochromator")
        # Set default macros
        # import pdb; pdb.set_trace()
        _macros = {
            "FES_STATE_PV": shutterA.state_pv,
            "FES_OPEN_PV": shutterA.open_signal.pvname,
            "FES_CLOSE_PV": shutterA.close_signal.pvname,
            "SCDS_STATE_PV": shutterCD.state_pv,
            "SCDS_OPEN_PV": shutterCD.open_signal.pvname,
            "SCDS_CLOSE_PV": shutterCD.close_signal.pvname,
            "ENERGY_PV": mono.energy.user_readback.pvname,
            "MONO_MODE_PV": mono.mode.prefix,
        }
        _macros.update(macros)
        super().__init__(args=args, macros=_macros, **kwargs)
    
    def ui_filename(self):
        return "status.ui"
