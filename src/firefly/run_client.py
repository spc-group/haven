import datetime as dt
import logging
from collections import OrderedDict
from typing import Sequence

from qtpy.QtCore import QObject, Slot, Signal
from tiled import queries

from haven import tiled_client


log = logging.getLogger(__name__)


class DatabaseWorker(QObject):
    selected_runs: Sequence = []
    _filters = {"exit_status": "success"}

    # Signals
    all_runs_changed = Signal(list)
    selected_runs_changed = Signal(list)
    distinct_fields_changed = Signal(dict)
    new_message = Signal(str, int)
    db_op_started = Signal()
    db_op_ended = Signal(list)  # (list of exceptions thrown)

    def __init__(self, root_node, *args, **kwargs):
        if root_node is None:
            root_node = tiled_client()
        self.root = root_node
        super().__init__(*args, **kwargs)

    def set_filters(self, filters):
        log.debug(f"Setting new filters: {filters}")
        self._filters = filters

    def filtered_nodes(self):
        case_sensitive = False
        runs = self.root
        filters = self._filters
        log.debug(f"Filtering nodes: {filters}")
        filter_params = [
            # (filter_name, query type, metadata key)
            ("user", queries.Regex, "proposal_users"),
            ("proposal", queries.Regex, "proposal_id"),
            ("esaf", queries.Regex, "esaf_id"),
            ("sample", queries.Regex, "sample_name"),
            # ('exit_status', queries.Regex, "exit_status"),
            ("plan", queries.Regex, "plan_name"),
            ("edge", queries.Regex, "edge"),
        ]
        for filter_name, Query, md_name in filter_params:
            val = filters.get(filter_name, "")
            if val != "":
                runs = runs.search(Query(md_name, val, case_sensitive=case_sensitive))
        full_text = filters.get("full_text", "")
        if full_text != "":
            runs = runs.search(
                queries.FullText(full_text, case_sensitive=case_sensitive)
            )
        return runs

    @Slot()
    def load_distinct_fields(self):
        """Get distinct metadata fields for filterable metadata.

        Emits
        =====
        distinct_fields_changed
          Emitted with the new dictionary of distinct metadata choices
          for each metadata key.

        """
        new_fields = {}
        target_fields = [
            "sample_name",
            "proposal_users",
            "proposal_id",
            "esaf_id",
            "sample_name",
            "plan_name",
            "edge",
        ]
        # Get fields from the database
        response = self.root.distinct(*target_fields)
        # Build into a new dictionary
        for key, result in response["metadata"].items():
            field = key.split(".")[-1]
            new_fields[field] = [r["value"] for r in result]
        self.distinct_fields_changed.emit(new_fields)

    @Slot()
    def load_all_runs(self):
        all_runs = []
        nodes = self.filtered_nodes()
        self.db_op_started.emit()
        try:
            for uid, node in nodes.items():
                # Get meta-data documents
                metadata = node.metadata
                start_doc = metadata.get("start")
                if start_doc is None:
                    log.debug(f"Skipping run with no start doc: {uid}")
                    continue
                stop_doc = node.metadata.get("stop")
                if stop_doc is None:
                    stop_doc = {}
                # Get a human-readable timestamp for the run
                timestamp = start_doc.get("time")
                if timestamp is None:
                    run_datetime = ""
                else:
                    run_datetime = dt.datetime.fromtimestamp(timestamp)
                    run_datetime = run_datetime.strftime("%Y-%m-%d %H:%M:%S")
                # Get the X-ray edge scanned
                edge = start_doc.get("edge")
                E0 = start_doc.get("E0")
                E0_str = "" if E0 is None else str(E0)
                if edge and E0:
                    edge_str = f"{edge} ({E0} eV)"
                elif edge:
                    edge_str = edge
                elif E0:
                    edge_str = E0_str
                else:
                    edge_str = ""
                # Build the table item
                # Get sample data from: dd80f432-c849-4749-a8f3-bdeec6f9c1f0
                run_data = OrderedDict(
                    plan_name=start_doc.get("plan_name", ""),
                    sample_name=start_doc.get("sample_name", ""),
                    edge=edge_str,
                    E0=E0_str,
                    exit_status=stop_doc.get("exit_status", ""),
                    run_datetime=run_datetime,
                    uid=uid,
                    proposal_id=start_doc.get("proposal_id", ""),
                    esaf_id=start_doc.get("esaf_id", ""),
                    esaf_users=start_doc.get("esaf_users", ""),
                )
                all_runs.append(run_data)
        except Exception as exc:
            self.db_op_ended.emit([exc])
            raise
        else:
            self.db_op_ended.emit([])
        self.all_runs_changed.emit(all_runs)

    @Slot(list)
    def load_selected_runs(self, uids):
        # Retrieve runs from the database
        uids = list(set(uids))
        self.db_op_started.emit()
        # Download each item, maybe we can find a more efficient way to do this
        try:
            runs = [self.root[uid] for uid in uids]
        except Exception as exc:
            self.db_op_ended.emit([exc])
            raise
        else:
            self.db_op_ended.emit([])
        # Save and inform clients of the run data
        self.selected_runs = runs
        self.selected_runs_changed.emit(runs)
