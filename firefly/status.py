import logging

import haven

from firefly import display, FireflyApplication

log = logging.getLogger(__name__)


class StatusDisplay(display.FireflyDisplay):
    def __init__(self, args=None, macros={}, **kwargs):
        _macros = {}
        # Set up macros for the A shutter
        try:
            shutterA = haven.registry.find(name="Shutter A", allow_none=False)
        except haven.exceptions.ComponentNotFound:
            msg = "COMPONENT_NOT_FOUND"
            log.warning("Could not find 'Shutter A' device in haven registry.")
            _macros.update(
                {
                    "FES_STATE_PV": msg,
                    "FES_OPEN_PV": msg,
                    "FES_CLOSE_PV": msg,
                }
            )
        else:
            _macros.update(
                {
                    "FES_STATE_PV": shutterA.state_pv,
                    "FES_OPEN_PV": shutterA.open_signal.pvname,
                    "FES_CLOSE_PV": shutterA.close_signal.pvname,
                }
            )
        # Set up the C or D hutch shutter
        try:
            shutters = haven.registry.findall(label="shutters", allow_none=False)
            shutterCD = [s for s in shutters if s.name != "Shutter A"][0]
        # except IndexError:
        #     # We only have one shutter, probably during testing
        #     # so for now we just reuse the A shutter.
        #     shutterCD = shutterA
        except (haven.exceptions.ComponentNotFound, IndexError):
            msg = "COMPONENT_NOT_FOUND"
            log.warning(
                "Could not find a C or D hutch shutter device in haven registry."
            )
            _macros.update(
                {
                    "SCDS_STATE_PV": msg,
                    "SCDS_OPEN_PV": msg,
                    "SCDS_CLOSE_PV": msg,
                }
            )
        else:
            _macros.update(
                {
                    "SCDS_STATE_PV": shutterCD.state_pv,
                    "SCDS_OPEN_PV": shutterCD.open_signal.pvname,
                    "SCDS_CLOSE_PV": shutterCD.close_signal.pvname,
                }
            )
        # Set default macros
        _macros.update(macros)
        super().__init__(args=args, macros=_macros, **kwargs)

    def customize_ui(self):
        app = FireflyApplication.instance()
        self.ui.bss_modify_button.clicked.connect(app.show_bss_window_action.trigger)

    def ui_filename(self):
        return "status.ui"
