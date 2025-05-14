from firefly import display


class UndulatorDisplay(display.FireflyDisplay):

    def customize_device(self):
        super().customize_device()
        self.setWindowTitle(self.device.name.title())

    def ui_filename(self):
        return "devices/undulator.ui"
