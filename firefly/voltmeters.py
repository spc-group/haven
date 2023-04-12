import json
import warnings
import logging

from pydm.widgets import PyDMEmbeddedDisplay
import haven

from firefly import display

# from .voltmeter import VoltmeterDisplay


log = logging.getLogger(__name__)


class VoltmetersDisplay(display.FireflyDisplay):
    _ion_chamber_displays = []

    # def __init__(
    #     self,
    #     args: Optional[Sequence] = None,
    #     macros: Mapping = {},
    #     **kwargs,
    # ):
    #     macros_ = macros.copy()
    #     scaler_ioc =
    #     macros_["SCALER"] == load_config()["ion_chamber"]["scaler"]["ioc"]
    #     super().__init__(args=args, macros=macros, **kwargs)

    def customize_ui(self):
        # Delete existing voltmeter widgets
        for idx in reversed(range(self.voltmeters_layout.count())):
            self.voltmeters_layout.takeAt(idx).widget().deleteLater()
        # Add embedded displays for all the ion chambers
        try:
            ion_chambers = list(haven.registry.findall(label="ion_chambers"))
        except haven.exceptions.ComponentNotFound as e:
            warnings.warn(str(e))
            log.warning(e)
            ion_chambers = []
        scaler_prefix = "CPT NOT FOUND"            
        self._ion_chamber_displays = []
        for ic in sorted(ion_chambers, key=lambda c: c.ch_num):
            # Get the scaler prefix for other macros
            if "SCALER" not in self.macros().keys():
                self._macros = dict(SCALER=ic.scaler_prefix, **self.macros())
            # Create the display object
            disp = PyDMEmbeddedDisplay(parent=self)
            disp.macros = json.dumps({"IC": ic.name})
            disp.filename = "voltmeter.py"
            # Add the Embedded Display to the Results Layout
            self.voltmeters_layout.addWidget(disp)
            self._ion_chamber_displays.append(disp)

    def ui_filename(self):
        return "voltmeters.ui"
