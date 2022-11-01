import json

from pydm.widgets import PyDMEmbeddedDisplay
import haven

from firefly import display
# from .voltmeter import VoltmeterDisplay



class VoltmetersDisplay(display.FireflyDisplay):
    _ion_chamber_displays = []

    def __init__(self, args=None, macros={}, **kwargs):
        self._ion_chamber_displays = []
        # Determine macros programatically from config file
        config = haven.load_config()['ion_chamber']['scaler']
        macros["PREFIX"] = macros.get("PREFIX", f"{config['ioc']}:{config['record']}")
        super().__init__(args=args, macros=macros, **kwargs)
    
    def customize_ui(self):
        # Delete existing voltmeter widgets
        for idx in reversed(range(self.voltmeters_layout.count())):
            self.voltmeters_layout.takeAt(idx).widget().deleteLater()
        # Add embedded displays for all the ion chambers
        ion_chambers = haven.registry.findall(label="ion_chambers")
        for ic in sorted(ion_chambers, key=lambda c: c.ch_num):
            disp = PyDMEmbeddedDisplay(parent=self)
            disp.macros = json.dumps({"CHANNEL_NUMBER": ic.ch_num,
                                      "PREAMP_PREFIX": ic.preamp_prefix,
                                      "PREFIX": ic.prefix})
            disp.filename = 'voltmeter.py'
            # Add the Embedded Display to the Results Layout
            self.voltmeters_layout.addWidget(disp)
            self._ion_chamber_displays.append(disp)

    def ui_filename(self):
        return "voltmeters.ui"
