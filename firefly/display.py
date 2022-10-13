from pathlib import Path

from pydm import Display


class FireflyDisplay(Display):
    def __init__(self, parent=None, args=None, macros=None, ui_filename=None, **kwargs):
        super().__init__(parent=parent, args=args, macros=macros, ui_filename=ui_filename, **kwargs)
        self.customize_device()
        self.customize_ui()

    def customize_device(self):
        pass

    def customize_ui(self):
        pass
    
    def ui_filename(self):
        raise NotImplementedError
    
    def ui_filepath(self):
        path_base = Path(__file__).parent
        return path_base / self.ui_filename()
