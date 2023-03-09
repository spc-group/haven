import logging

from apsbss import apsbss
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtCore import Signal, Slot

import haven
from firefly import display

log = logging.getLogger(__name__)


class BssDisplay(display.FireflyDisplay):
    """A PyDM display for the beamline scheduling system (BSS)."""

    _proposal_col_names = ["id", "title", "startTime", "endTime"]
    _esaf_col_names = [
        "esafId",
        "esafTitle",
        "experimentStartDate",
        "experimentEndDate",
    ]

    # Signal
    proposal_changed = Signal()
    esaf_changed = Signal()

    def __init__(self, api=apsbss, args=None, macros={}, **kwargs):
        self.api = api
        # Set up macros
        try:
            bss = haven.registry.find(name="bss")
        except haven.exceptions.ComponentNotFound:
            log.warning("Could not find bss device in Haven registry.")
            macros["P"] = "COMPONENT_NOT_FOUND"
        else:
            macros["P"] = bss.prefix
        super().__init__(args=args, macros=macros, **kwargs)
        # Load data models for proposals and ESAFs
        self.load_models()

    def load_models(self):
        config = haven.load_config()
        # Create proposal model object
        col_names = self._proposal_col_names
        self.proposal_model = QStandardItemModel()
        header_labels = [c.title() for c in col_names]
        self.proposal_model.setHorizontalHeaderLabels(header_labels)
        # Load individual proposals
        proposals = self.api.getCurrentProposals(config["bss"]["beamline"])
        for proposal in proposals:
            items = [QStandardItem(str(proposal[col])) for col in col_names]
            self.proposal_model.appendRow(items)
        self.ui.proposal_view.setModel(self.proposal_model)
        # Create proposal model object
        col_names = self._esaf_col_names
        self.esaf_model = QStandardItemModel()
        header_labels = [c.title() for c in col_names]
        self.esaf_model.setHorizontalHeaderLabels(header_labels)
        # Load individual esafs
        esafs = self.api.getCurrentEsafs(config["bss"]["beamline"].split("-")[0])
        for esaf in esafs:
            items = [QStandardItem(str(esaf[col])) for col in col_names]
            self.esaf_model.appendRow(items)
        self.ui.esaf_view.setModel(self.esaf_model)
        # Connect slots for when proposal/ESAF is changed
        self.ui.proposal_view.selectionModel().currentChanged.connect(
            self.update_proposal
        )
        self.ui.esaf_view.selectionModel().currentChanged.connect(self.update_esaf)

    def update_proposal(self, current, previous):
        # Determine which proposal was selected
        id_col_idx = self._proposal_col_names.index("id")
        new_id = current.siblingAtColumn(id_col_idx).data()
        # Change the proposal in the EPICS record
        bss = haven.registry.find(name="bss")
        bss.proposal.proposal_id.set(new_id).wait()
        self.api.epicsUpdate(bss.prefix)
        # Notify any interested parties that the proposal has been changed
        self.proposal_changed.emit()

    def update_esaf(self, current, previous):
        # Determine which esaf was selected
        id_col_idx = self._esaf_col_names.index("esafId")
        new_id = current.siblingAtColumn(id_col_idx).data()
        # Change the esaf in the EPICS record
        bss = haven.registry.find(name="bss")
        bss.wait_for_connection()
        bss.esaf.esaf_id.set(new_id).wait(timeout=5)
        self.api.epicsUpdate(bss.prefix)
        # Notify any interested parties that the esaf has been changed
        self.esaf_changed.emit()

    def ui_filename(self):
        return "bss.ui"
