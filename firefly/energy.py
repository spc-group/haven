from qtpy import QtWidgets

from haven import registry, load_config
from firefly import display


class EnergyDisplay(display.FireflyDisplay):
    caqtdm_ui_file = "/net/s25data/xorApps/ui/DCMControlCenter.ui"

    def __init__(self, args=None, macros={}, **kwargs):
        # Set up macros
        mono = registry.find(name="monochromator")
        _macros = dict(**macros)
        _macros["MONO_MODE_PV"] = _macros.get("MONO_MODE_PV", mono.mode.pvname)
        _macros["MONO_ENERGY_PV"] = _macros.get("MONO_ENERGY_PV", mono.energy.user_readback.pvname)
        energy = registry.find(name="energy")
        _macros["ID_ENERGY_PV"] = _macros.get("ID_ENERGY_PV", f"{energy.id_prefix}:Energy.VAL")
        _macros["ID_GAP_PV"] = _macros.get("ID_GAP_PV", f"{energy.id_prefix}:Gap.VAL")
        super().__init__(args=args, macros=_macros, **kwargs)

    def launch_mono_caqtdm(self):
        config = load_config()
        display_macros = self.macros()
        prefix = config["monochromator"]["ioc"] + ":"
        caqtdm_macros = {
            "P": prefix,
            "MONO": config["monochromator"]["ioc_branch"],
            "BRAGG": registry.find(name="monochromator_bragg").prefix.replace(prefix, ""),
            "GAP": registry.find(name="monochromator_gap").prefix.replace(prefix, ""),
            "ENERGY": registry.find(name="monochromator_energy").prefix.replace(prefix, ""),
            "OFFSET": registry.find(name="monochromator_offset").prefix.replace(prefix, ""),
            "IDENERGY": display_macros["ID_ENERGY_PV"],
        }
        self.launch_caqtdm(macros=caqtdm_macros)

    def customize_ui(self):
        self.ui.mono_caqtdm_button.clicked.connect(
            self.launch_mono_caqtdm)

    def ui_filename(self):
        return "energy.ui"
