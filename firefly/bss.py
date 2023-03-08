import logging

from apsbss import apsbss
from qtpy.QtGui import QStandardItemModel, QStandardItem

import haven
from firefly import display

log = logging.getLogger(__name__)


class BssDisplay(display.FireflyDisplay):
    """A PyDM display for the beamline scheduling system (BSS)."""
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
        # Create model objects
        self.proposal_model = QStandardItemModel()
        col_names = ["id", "title"]
        header_labels = [c.title() for c in col_names]
        self.proposal_model.setHorizontalHeaderLabels(header_labels)
        from pprint import pprint
        # self.ui.proposal_view.currentChanged().connect(self.proposal_changed)
        # Load individual proposals
        proposals = self.api.getCurrentProposals(config['bss']['beamline'])
        for proposal in proposals:
            items = [QStandardItem(str(proposal[col])) for col in col_names]
            self.proposal_model.appendRow(items)
        self.ui.proposal_view.setModel(self.proposal_model)
        # Connect slots for when proposal is changed
        self.ui.proposal_view.selectionModel().currentChanged.connect(
            self.proposal_changed)

    def proposal_changed(self, current, previous):
        print("Changed", current, previous)
        
    def ui_filename(self):
        return "bss.ui"
