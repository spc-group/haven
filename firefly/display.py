import subprocess
from pathlib import Path

from pydm import Display


class FireflyDisplay(Display):
    caqtdm_ui_file: str = ""
    caqtdm_command: str = "/APSshare/bin/caQtDM -style plastique -noMsg"

    def __init__(self, parent=None, args=None, macros=None, ui_filename=None, **kwargs):
        super().__init__(
            parent=parent, args=args, macros=macros, ui_filename=ui_filename, **kwargs
        )
        self.customize_device()
        self.customize_ui()
        self.find_plan_widgets()

    def _all_children(self, widget):
        for child in widget.children():
            yield widget
            yield from self._all_children(widget=child)

    def find_plan_widgets(self):
        """Look through widgets and determine if any of them are used for
        bluesky plans.

        """
        # from pprint import pprint
        # pprint([c.objectName() for c in self._all_children(self)])
        # for child in self.ui.children():
        #     if child.objectName() == "set_energy_button":
        #         print(f"**{child.objectName()}**")
        #     else:
        #         print(child.objectName())

    def launch_caqtdm(self, macros={}, ui_file: str = None):
        """Launch a caQtDM window showing the window's panel."""
        if ui_file is None:
            ui_file = self.caqtdm_ui_file
        cmds = self.caqtdm_command.split()
        macro_str = ",".join(f"{key}={val}" for key, val in macros.items())
        cmds = [*cmds, "-macro", macro_str, ui_file]
        subprocess.Popen(cmds)

    def customize_device(self):
        pass

    def customize_ui(self):
        pass

    def ui_filename(self):
        raise NotImplementedError

    def ui_filepath(self):
        path_base = Path(__file__).parent
        return path_base / self.ui_filename()
