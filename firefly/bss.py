import logging

from apsbss import apsbss
from qtpy.QtGui import QStandardItemModel, QStandardItem

import haven
from firefly import display

log = logging.getLogger(__name__)


class BssDisplay(display.FireflyDisplay):
    """A PyDM display for the beamline scheduling system (BSS)."""
    def __init__(self, api=apsbss, *args, **kwargs):
        self.api = api
        super().__init__(*args, **kwargs)
        self.load_models()

    def load_models(self):
        print("LOading models")
        config = haven.load_config()
        # Create model objects
        self.proposal_model = QStandardItemModel()
        col_names = ["id", "title"]
        # Load individual proposals
        proposals = self.api.getCurrentProposals(config['bss']['beamline'])
        print(f"Loading proposals: {proposals}")
        for proposal in proposals:
            items = [QStandardItem(proposal[col]) for col in col_names]
            self.proposal_model.appendRow(items)
        self.ui.proposal_view.setModel(self.proposal_model)

    def ui_filename(self):
        return "bss.ui"
