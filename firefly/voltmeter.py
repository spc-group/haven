import display


class VoltmeterDisplay(display.FireflyDisplay):
    def customize_ui(self):
        print(self.macros())
        print(dir(self.ui))
    
    def ui_filename(self):
        return "voltmeter.ui"
