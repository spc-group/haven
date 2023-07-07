import subprocess
from pathlib import Path

from qtpy.QtCore import Signal
from pydm import Display


class FireflyDisplay(Display):
    caqtdm_ui_file: str = ""
    caqtdm_command: str = "/APSshare/bin/caQtDM -style plastique -noMsg"

    # Signals
    status_message_changed = Signal(str, int)

    def __init__(self, parent=None, args=None, macros=None, ui_filename=None, **kwargs):
        super().__init__(
            parent=parent, args=args, macros=macros, ui_filename=ui_filename, **kwargs
        )
        self.customize_device()
        self.customize_ui()

    def _open_caqtdm_subprocess(self, cmds, *args, **kwargs):
        """Launch a new subprocess and save it to self._caqtdm_process."""
        # Try to leave this as just a simple call to Popen.
        # It helps simplify testing
        self._caqtdm_process = subprocess.Popen(cmds, *args, **kwargs)

    def launch_caqtdm(self, macros={}, ui_file: str = None):
        """Launch a caQtDM window showing the window's panel."""
        if ui_file is None:
            ui_file = self.caqtdm_ui_file
        cmds = self.caqtdm_command.split()
        macro_str = ",".join(f"{key}={val}" for key, val in macros.items())
        cmds = [*cmds, "-macro", macro_str, ui_file]
        self._open_caqtdm_subprocess(cmds)

    def customize_device(self):
        pass

    def customize_ui(self):
        pass

    def show_message(self, message, timeout=0):
        """Display a message in the status bar."""
        self.status_message_changed.emit(str(message), timeout)

    def ui_filename(self):
        raise NotImplementedError

    def ui_filepath(self):
        path_base = Path(__file__).parent
        return path_base / self.ui_filename()
