from pathlib import Path

from pydm import Display


class FireflyDisplay(Display):
    def ui_filename(self):
        raise NotImplementedError
    
    def ui_filepath(self):
        path_base = Path(__file__).parent
        return path_base / self.ui_filename()
