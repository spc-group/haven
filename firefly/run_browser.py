import logging
import datetime as dt

from qtpy.QtGui import QStandardItemModel, QStandardItem

from firefly import display, FireflyApplication
from haven import tiled_client, load_config

log = logging.getLogger(__name__)


class RunBrowserDisplay(display.FireflyDisplay):
    # def customize_ui(self):
    #     app = FireflyApplication.instance()
    #     self.ui.bss_modify_button.clicked.connect(app.show_bss_window_action.trigger)

    runs_model: QStandardItemModel

    def __init__(self, client=None, args=None, macros=None, **kwargs):
        config = load_config()
        if client is None:
            client = tiled_client(entry_node=config['database']['tiled']['entry_node'])
        self.client = client
        super().__init__(args=args, macros=macros, **kwargs)
        self.load_models()

    def load_models(self):
        # Set up the model
        col_names = ["UID", "Plan", "Sample", "Datetime", "Proposal", "ESAF", "Edge"]
        self.runs_model = QStandardItemModel()
        self.runs_model.setHorizontalHeaderLabels(col_names)
        # Add the model to the UI element
        self.ui.run_table.setModel(self.runs_model)
        self.load_data()

    def load_data(self):
        for uid, node in self.client.items():
            metadata = node.metadata
            try:
                start_doc = node.metadata['start']
            except KeyError:
                log.debug(f"Skipping run with no start doc: {uid}")
                continue
            from pprint import pprint
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
            # col_names = ["UID", "Plan", "Sample", "Datetime", "Proposal", "ESAF", "Edge"]
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
