import logging

from qtpy import QtWidgets, QtCore
from bluesky_queueserver_api import BPlan
from haven import registry, load_config
from xraydb.xraydb import XrayDB

from firefly import display


log = logging.getLogger(__name__)


class EnergyDisplay(display.FireflyDisplay):
    caqtdm_mono_ui_file = "/net/s25data/xorApps/ui/DCMControlCenter.ui"
    caqtdm_id_ui_file = "/net/s25data/xorApps/epics/synApps_6_2/ioc/25ida/25idaApp/op/ui/IDControl.ui"
    min_energy = 4000
    max_energy = 27000
    stylesheet_danger = "background: rgb(220, 53, 69); color: white; border-color: rgb(220, 53, 69)"
    stylesheet_normal = ""

    def __init__(self, args=None, macros={}, **kwargs):
        # Set up macros
        mono = registry.find(name="monochromator")
        _macros = dict(**macros)
        _macros["MONO_MODE_PV"] = _macros.get("MONO_MODE_PV", mono.mode.pvname)
        _macros["MONO_ENERGY_PV"] = _macros.get("MONO_ENERGY_PV", mono.energy.user_readback.pvname)
        energy = registry.find(name="energy")
        _macros["ID_ENERGY_PV"] = _macros.get("ID_ENERGY_PV", f"{energy.id_prefix}:Energy.VAL")
        _macros["ID_GAP_PV"] = _macros.get("ID_GAP_PV", f"{energy.id_prefix}:Gap.VAL")
        # Load X-ray database for calculating edge energies
        self.xraydb = XrayDB()
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
        self.launch_caqtdm(macros=caqtdm_macros, ui_file=self.caqtdm_mono_ui_file)

    def launch_id_caqtdm(self):
        """Launch the pre-built caQtDM UI file for the ID."""
        config = load_config()
        prefix = config["undulator"]["ioc"]
        # Strip leading "ID" from the mono IOC since caQtDM adds it
        prefix = prefix.strip("ID")
        caqtdm_macros = {
            # No idea what "M", and "D" do, they're not in the UI
            # file.
            "ID": prefix,
            "M": 2,
            "D": 2,
        }
        self.launch_caqtdm(macros=caqtdm_macros, ui_file=self.caqtdm_id_ui_file)

    def set_energy(self, *args, **kwargs):
        energy = float(self.ui.target_energy_lineedit.text())
        log.info(f"Setting new energy: {energy}")
        # Build the queue item
        item = BPlan("set_energy", energy=energy)
        # Submit the item to the queueserver
        app = QtWidgets.QApplication.instance()
        app.add_queue_item(item)

    def customize_ui(self):
        self.ui.mono_caqtdm_button.clicked.connect(self.launch_mono_caqtdm)
        self.ui.id_caqtdm_button.clicked.connect(self.launch_id_caqtdm)
        self.ui.set_energy_button.clicked.connect(self.set_energy)
        # Set up the combo box with X-ray energies
        combo_box = self.ui.edge_combo_box
        ltab = self.xraydb.tables['xray_levels']
        edges = self.xraydb.query(ltab)
        edges = edges.filter(ltab.c.absorption_edge < self.max_energy,
                             ltab.c.absorption_edge > self.min_energy)
        items = [f"{r.element} {r.iupac_symbol} ({int(r.absorption_edge)} eV)"
                 for r in edges.all()]
        combo_box.addItems(["Select edge…", *items])
        combo_box.activated.connect(self.select_edge)

    @QtCore.Slot(int)
    def select_edge(self, index):
        if index == 0:
            # The placeholder text was selected
            return
        # Parse the combo box text to get the selected edge
        combo_box = self.ui.edge_combo_box
        text = combo_box.itemText(index)
        elem, edge = text.replace(" ", "_").split("_")[:2]
        # Determine which energy was selected
        edge_info = self.xraydb.xray_edge(element=elem, edge=edge)
        if edge_info is None:
            # Edge is not recognized, so provide feedback
            combo_box.setStyleSheet(self.stylesheet_danger)
        else:
            # Set the text field to the selected edge's energy            
            energy, fyield, edge_jump = edge_info
            self.ui.target_energy_lineedit.setText(f"{energy:.3f}")
            combo_box.setStyleSheet(self.stylesheet_normal)

    def ui_filename(self):
        return "energy.ui"
