import haven
from firefly import display
from haven.instrument import mirrors
from firefly.slits import SlitsDisplay


class MirrorDisplay(SlitsDisplay):
    caqtdm_ui_filenames = {
        mirrors.HighHeatLoadMirror: "/net/s25data/xorApps/epics/synApps_6_2/ioc/25ida/25idaApp/op/ui/HHLM_4.ui",
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
        MIR = pieces[-1]
        caqtdm_macros = {
            "P": P,
            "MIR": pieces[-1],
            "Y": self.device.transverse.prefix.split(":")[-1],
            "ROLL": self.device.roll.prefix.split(":")[-1],
            "LAT": self.device.normal.prefix.split(":")[-1],
            "CP": self.device.pitch.prefix.split(":")[-1],
            "UPL": self.device.upstream.prefix.split(":")[-1],
            "DNL": self.device.downstream.prefix.split(":")[-1],
        }
        # Launch the caQtDM panel
        super(SlitsDisplay, self).launch_caqtdm(macros=caqtdm_macros)
