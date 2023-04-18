import logging
import datetime as dt
from typing import Sequence
import pprint
import json
import yaml

from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtCore import Signal, Slot

from firefly import display, FireflyApplication
from haven import tiled_client, load_config

log = logging.getLogger(__name__)


class RunBrowserDisplay(display.FireflyDisplay):
    # def customize_ui(self):
    #     app = FireflyApplication.instance()
    #     self.ui.bss_modify_button.clicked.connect(app.show_bss_window_action.trigger)

    runs_model: QStandardItemModel
    _run_col_names: Sequence = ["UID", "Plan", "Sample", "Datetime", "Proposal", "ESAF", "Edge"]

    # Signals
    runs_selected = Signal(list)

    def __init__(self, client=None, args=None, macros=None, **kwargs):
        config = load_config()
        if client is None:
            client = tiled_client(entry_node=config['database']['tiled']['entry_node'])
        self.client = client
        super().__init__(args=args, macros=macros, **kwargs)

    def customize_ui(self):
        # Setup controls for select which run to show
        self.load_models()
        self.ui.run_tableview.selectionModel().selectionChanged.connect(
            self.select_runs
        )
        self.runs_selected.connect(self.update_metadata)

    def update_metadata(self, runs):
        """Render metadata for the runs into the metadata widget."""
        # Combine the metadata in a human-readable output
        text = ""
        for run in runs:
            md_dict = dict(**run.metadata)
            text += yaml.dump(md_dict)
            text += f"\n\n{'=' * 20}\n\n"
        # Update the widget with the rendered metadata
        self.ui.metadata_textedit.document().setPlainText(text)

    def select_runs(self, selected, deselected):
        # Get UID's from the selection
        col_idx = self._run_col_names.index("UID")
        indexes = self.ui.run_tableview.selectedIndexes() 
        uids = [i.siblingAtColumn(col_idx).data() for i in indexes]
        # Retrieve runs from the database
        runs = [self.client[uid] for uid in uids]
        self.runs_selected.emit(runs)

    def load_models(self):
        # Set up the model
        col_names = self._run_col_names
        self.runs_model = QStandardItemModel()
        self.runs_model.setHorizontalHeaderLabels(col_names)
        # Add the model to the UI element
        self.ui.run_tableview.setModel(self.runs_model)
        self.load_list_of_runs()

    def load_list_of_runs(self):
        for uid, node in self.client.items():
            metadata = node.metadata
            try:
                start_doc = node.metadata['start']
            except KeyError:
                log.debug(f"Skipping run with no start doc: {uid}")
                continue
            # Get a human-readable timestamp for the run
            timestamp = start_doc.get('time')
            if timestamp is None:
                run_datetime = ""
            else:
                run_datetime = dt.datetime.fromtimestamp(timestamp)
                run_datetime = run_datetime.strftime("%Y-%m-%d %H:%M:%S")
            # Get the X-ray edge scanned
            edge = start_doc.get("edge")
            E0 = start_doc.get("E0")
            if edge and E0:
                edge_str = f"{edge} ({E0} eV)"
            elif edge:
                edge_str = edge
            elif E0:
                edge_str = str(E0)
            else:
                edge_str = ""
            # Build the table item
            # Get sample data from: dd80f432-c849-4749-a8f3-bdeec6f9c1f0
            items = [
                uid,
                start_doc.get('plan_name', ""),
                start_doc.get('sample_name', ""),
                run_datetime,
                start_doc.get("proposal_id", ""),
                start_doc.get("esaf_id", ""),
                edge_str,
            ]
            try:
                items = [QStandardItem(item) for item in items]
            except:
                print(items)
                raise
            self.ui.runs_model.appendRow(items)

    def ui_filename(self):
        return "run_browser.ui"
