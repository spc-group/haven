import display


class XafsScanRegionDisplay(display.FireflyDisplay):
    def ui_filename(self):
        return "xafs_scan_region.ui"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        obj = self.ui
        print(type(obj), dir(obj))
    
