import datetime as dt
import logging
from collections import OrderedDict
from typing import Sequence

from qtpy.QtCore import QObject, Slot, Signal

from haven import tiled_client


log = logging.getLogger(__name__)

class DatabaseWorker(QObject):

    selected_runs: Sequence = []

    # Signals
    all_runs_changed = Signal(list)
    selected_runs_changed = Signal(list)

    def __init__(self, root_node, *args, **kwargs):
        if root_node is None:
            root_node = tiled_client()
        self.root = root_node
        super().__init__(*args, **kwargs)

    @Slot()
    def load_all_runs(self):
        all_runs = []
        for uid, node in self.root.items():
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
            run_data = OrderedDict(
                uid=uid,
                plan_name=start_doc.get('plan_name', ""),
                sample_name=start_doc.get('sample_name', ""),
                run_datetime=run_datetime,
                proposal_id=start_doc.get("proposal_id", ""),
                esaf_id=start_doc.get("esaf_id", ""),
                edge=edge_str,
            )
            all_runs.append(run_data)
        self.all_runs_changed.emit(all_runs)

    @Slot(list)
    def load_selected_runs(self, uids):
        # Retrieve runs from the database
        runs = [self.root[uid] for uid in uids]
        self.selected_runs = runs
        self.selected_runs_changed.emit(runs)
