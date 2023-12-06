import haven
from firefly import display
from haven.instrument import mirrors
from firefly.slits import SlitsDisplay


class KBMirrorsDisplay(SlitsDisplay):
    caqtdm_ui_filenames = {
        mirrors.KBMirrors: "/net/s25data/xorApps/ui/KB_mirrors.ui",
    }

    def ui_filename(self):
        return "kb_mirrors.ui"

    def launch_caqtdm(self):
        # Sort out the prefix from the slit designator
        prefix = self.device.prefix.strip(":")
        pieces = prefix.split(":")
        # Build the macros for the caQtDM panels
        P = ":".join(pieces[:-1])
        P = f"{P}:"
        KB = pieces[-1]
        KBH = self.device.horiz.prefix.replace(P, "")
        KBV = self.device.vert.prefix.replace(P, "")
        caqtdm_macros = {
            "P": f"{P}",
            "KB": KB,
            "KBH": KBH,
            "KBV": KBV,
        }
        # Launch the caQtDM panel
        super(SlitsDisplay, self).launch_caqtdm(macros=caqtdm_macros)
