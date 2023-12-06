import haven
from firefly import display
from haven.instrument import slits


class SlitsDisplay(display.FireflyDisplay):
    caqtdm_ui_filenames = {
        slits.BladeSlits: "/APSshare/epics/synApps_6_2_1/support/optics-R2-13-5//opticsApp/op/ui/autoconvert/4slitGraphic.ui",
        slits.ApertureSlits: "/net/s25data/xorApps/epics/synApps_6_2/ioc/25ida/25idaApp/op/ui/maskApertureSlit.ui",
    }

    def customize_device(self):
        self.device = haven.registry.find(self.macros()["DEVICE"])

    def ui_filename(self):
        return "slits.ui"

    @property
    def caqtdm_ui_file(self):
        # Go up the class list until we find a class that is recognized
        for Cls in self.device.__class__.__mro__:
            try:
                return self.caqtdm_ui_filenames[Cls]
            except KeyError:
                continue
        # We didn't find any supported classes of slits
        raise KeyError("Could not find caQtDM filename for optic "
                       f"{self.device.name} ({self.device.__class__}).")

    def launch_caqtdm(self):
        # Sort out the prefix from the slit designator
        prefix = self.device.prefix.strip(":")
        pieces = prefix.split(":")
        # Build the macros for the caQtDM panels
        P = ":".join(pieces[:-1])
        SLIT = ":".join(pieces[-1:])
        H = self.device.h.prefix.split(":")[1]
        V = self.device.v.prefix.split(":")[1]
        caqtdm_macros = {
            "P": f"{P}:",
            "SLIT": SLIT,  # For 4-blade slits
            "SLITS": SLIT,  # For rotary aperture slits
            "H": H,  # For 4-blade slits
            "V": V,  # For 4-blade slits
        }
        # Launch the caQtDM panel
        super().launch_caqtdm(macros=caqtdm_macros)
