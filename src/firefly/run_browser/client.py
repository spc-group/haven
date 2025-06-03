import asyncio
import datetime as dt
import logging
import warnings
from collections import ChainMap, OrderedDict
from collections.abc import Generator
from functools import partial
from typing import Mapping, Sequence

import httpx
import numpy as np
import pandas as pd
from tiled import queries

from haven import exceptions
from haven.catalog import Catalog, _search, resolve_uri

log = logging.getLogger(__name__)


class DatabaseWorker:
    selected_runs: Sequence = []
    catalog: Catalog = None

    def __init__(self, base_url: str = "http://localhost:8000"):
        uri = resolve_uri(base_url)
        self.client = httpx.AsyncClient(base_url=uri, timeout=20, http2=True)

    def change_catalog(self, catalog_name: str):
        """Change the catalog being used for pulling data.

        *catalog_name* should be an entry in *worker.tiled_client()*.
        """
        self.catalog = Catalog(path=catalog_name, client=self.client)

    async def catalog_names(self):
        catalogs = _search(path="", client=self.client)
        return [cat["id"] async for cat in catalogs]

    async def stream_names(self):
        awaitables = [scan.stream_names() for scan in self.selected_runs]
        all_streams = await asyncio.gather(*awaitables)
        # Flatten the lists
        streams = [stream for streams in all_streams for stream in streams]
        return list(set(streams))

    async def data_keys(self, stream: str):
        aws = [run.data_keys(stream=stream) for run in self.selected_runs]
        keys = await asyncio.gather(*aws)
        keys = ChainMap(*keys)
        keys["seq_num"] = {
            "dtype": "number",
            "dtype_numpy": "<i8",
            "precision": 0,
            "shape": [],
        }
        return keys

    async def data_frames(self, stream: str) -> dict:
        """Return the internal dataframes for selected runs as {uid: dataframe}."""
        if len(self.selected_runs) == 0:
            return {}
        aws = [run.data(stream=stream) for run in self.selected_runs]
        aws += [run.uid for run in self.selected_runs]
        results = await asyncio.gather(*aws)
        dfs = results[: len(results) // 2]
        uids = results[len(results) // 2 :]
        return {uid: df for uid, df in zip(uids, dfs)}

    async def filtered_runs(self, filters: Mapping):
        log.debug(f"Filtering nodes: {filters}")
        filter_params = {
            # filter_name: (query type, metadata key)
            "plan": (queries.Eq, "start.plan_name"),
            "sample": (queries.Contains, "start.sample_name"),
            "formula": (queries.Contains, "start.sample_formula"),
            "scan": (queries.Contains, "start.scan_name"),
            "edge": (queries.Contains, "start.edge"),
            "exit_status": (queries.Eq, "stop.exit_status"),
            "user": (queries.Contains, "start.proposal_users"),
            "proposal": (queries.Eq, "start.proposal_id"),
            "esaf": (queries.Eq, "start.esaf_id"),
            "beamline": (queries.Eq, "start.beamline_id"),
            "before": (partial(queries.Comparison, "le"), "stop.time"),
            "after": (partial(queries.Comparison, "ge"), "start.time"),
            "full_text": (queries.FullText, ""),
            "standards_only": (queries.Eq, "start.is_standard"),
        }
        # Apply filters
        _queries = []
        for filter_name, filter_value in filters.items():
            if filter_name not in filter_params:
                continue
            Query, md_name = filter_params[filter_name]
            if Query is queries.FullText:
                query = Query(filter_value)
            else:
                query = Query(md_name, filter_value)
            _queries.append(query)
        async for run in self.catalog.runs(queries=_queries):
            yield run

    async def distinct_fields(self) -> Generator[tuple[str, dict], None, None]:
        """Get distinct metadata fields for filterable metadata."""
        new_fields = {}
        # Some of these are disabled since they take forever
        # (could be re-enabled when switching to postgres)
        target_fields = [
            "start.plan_name",
            # "start.sample_name",
            # "start.sample_formula",
            # "start.scan_name",
            "start.edge",
            "stop.exit_status",
            # "start.proposal_id",
            # "start.esaf_id",
            "start.beamline_id",
        ]
        # Get fields from the database
        async for distinct in self.catalog.distinct(*target_fields):
            field_name = list(distinct.keys())[0]
            fields = distinct[field_name]
            fields = [field["value"] for field in fields]
            fields = [field for field in fields if field not in ["", None]]
            yield field_name, fields

    async def load_all_runs(self, filters: Mapping = {}):
        all_runs = []
        runs = self.filtered_runs(filters=filters)
        async for run in runs:
            # Get meta-data documents
            metadata = await run.metadata
            start_doc = metadata.get("start")
            if start_doc is None:
                log.debug(f"Skipping run with no start doc: {run.path}")
                continue
            stop_doc = metadata.get("stop")
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
            # Combine sample and formula together
            sample_name = start_doc.get("sample_name", "")
            formula = start_doc.get("sample_formula", "")
            if sample_name and formula:
                sample_str = f"{sample_name} ({formula})"
            else:
                sample_str = sample_name or formula
            # Build the table item
            # Get sample data from: dd80f432-c849-4749-a8f3-bdeec6f9c1f0
            run_data = OrderedDict(
                plan_name=start_doc.get("plan_name", ""),
                sample_name=sample_str,
                scan_name=start_doc.get("scan_name", ""),
                edge=edge_str,
                exit_status=stop_doc.get("exit_status", ""),
                run_datetime=run_datetime,
                uid=start_doc.get("uid", ""),
            )
            all_runs.append(run_data)
        return all_runs

    async def hints(self, stream: str = "primary") -> tuple[list, list]:
        """Get hints for this stream, as two lists.

        (*independent_hints*, *dependent_hints*)

        *independent_hints* are those operated by the experiment,
         while *dependent_hints* are those measured as a result.
        """
        aws = [run.hints(stream) for run in self.selected_runs]
        all_hints = await asyncio.gather(*aws)
        # Flatten arrays
        try:
            ihints, dhints = zip(*all_hints)
        except ValueError:
            ihints, dhints = [], []
        ihints = [hint for hints in ihints for hint in hints]
        dhints = [hint for hints in dhints for hint in hints]
        return ihints, dhints

    async def signal_names(self, stream: str, *, hinted_only: bool = False):
        """Get a list of valid signal names (data columns) for selected runs.

        Parameters
        ==========
        stream
          The Tiled stream name to fetch.
        hinted_only
          If true, only signals with the kind="hinted" parameter get
          picked.

        """
        xsignals, ysignals = [], []
        for run in self.selected_runs:
            if hinted_only:
                xsig, ysig = await run.hints(stream=stream)
            else:
                df = await run.data(stream=stream)
                xsig = ysig = df.columns
            xsignals.extend(xsig)
            ysignals.extend(ysig)
        # Remove duplicates
        xsignals = list(dict.fromkeys(xsignals))
        ysignals = list(dict.fromkeys(ysignals))
        return list(xsignals), list(ysignals)

    async def metadata(self):
        """Get all metadata for the selected runs in one big dictionary."""
        md = {}
        if len(self.selected_runs) == 0:
            warnings.warn("No runs selected, metadata will be empty.")
        for run in self.selected_runs:
            md[str(run.path)] = await run.metadata
        return md

    def load_selected_runs(self, uids):
        # Prepare the query for finding the runs
        uids = list(dict.fromkeys(uids))
        # Retrieve runs from the database
        runs = [self.catalog[uid] for uid in uids]
        # runs = await asyncio.gather(*run_coros)
        self.selected_runs = runs
        return runs

    async def images(self, signal: str, stream: str):
        """Load the selected runs as 2D or 3D images suitable for plotting."""
        images = OrderedDict()
        for idx, run in enumerate(self.selected_runs):
            # Load datasets from the database
            try:
                image = await run.__getitem__(signal, stream=stream)
            except KeyError as exc:
                log.exception(exc)
            else:
                images[run.uid] = image
        return images

    async def all_signals(self, stream: str, *, hinted_only=False) -> dict:
        """Produce dataframes with all signals for each run.

        The keys of the dictionary are the labels for each curve, and
        the corresponding value is a pandas dataframe with the scan data.

        """
        xsignals, ysignals = await self.signal_names(
            hinted_only=hinted_only, stream=stream
        )
        # Build the dataframes
        dfs = OrderedDict()
        for run in self.selected_runs:
            # Get data from the database
            df = await run.data(signals=xsignals + ysignals, stream=stream)
            dfs[run.uid] = df
        return dfs

    async def dataset(
        self,
        dataset_name: str,
        *,
        stream: str,
        uids: Sequence[str] | None = None,
    ) -> Mapping:
        """Produce a dictionary with the n-dimensional datasets for plotting.

        The keys of the dictionary are the UIDs for each scan, and
        the corresponding value is a pandas dataset with the data for
        each signal.

        Parameters
        ==========
        uids
          If not ``None``, only runs with UIDs listed in this
          parameter will be included.

        """
        # Build the dataframes
        arrays = OrderedDict()
        for run in self.selected_runs:
            # Get data from the database
            arr = await run.external_dataset(dataset_name, stream=stream)
            arrays[run.uid] = arr
        return arrays

    async def signals(
        self,
        x_signal,
        y_signal,
        r_signal=None,
        *,
        stream: str,
        use_log=False,
        use_invert=False,
        use_grad=False,
        uids: Sequence[str] | None = None,
    ) -> Mapping:
        """Produce a dictionary with the 1D datasets for plotting.

        The keys of the dictionary are the labels for each curve, and
        the corresponding value is a pandas dataset with the data for
        each signal.

        Parameters
        ==========
        uids
          If not ``None``, only runs with UIDs listed in this
          parameter will be included.

        """
        # Check for sensible inputs
        use_reference = r_signal is not None
        if "" in [x_signal, y_signal] or (use_reference and r_signal == ""):
            msg = (
                f"Empty signal name requested: x={repr(x_signal)}, y={repr(y_signal)},"
                f" r={repr(r_signal)}"
            )
            log.debug(msg)
            raise exceptions.EmptySignalName(msg)
        signals = [x_signal, y_signal]
        if use_reference:
            signals.append(r_signal)
        # Remove duplicates
        signals = list(dict.fromkeys(signals).keys())
        # Build the dataframes
        dfs = OrderedDict()
        for run in self.selected_runs:
            # Check that the UID matches
            if uids is not None and run.uid not in uids:
                break
            # Get data from the database
            df = await run.data(signals=signals, stream=stream)
            # Check for missing signals
            missing_x = x_signal not in df.columns and df.index.name != x_signal
            missing_y = y_signal not in df.columns
            missing_r = r_signal not in df.columns
            if missing_x or missing_y or (use_reference and missing_r):
                log.warning(
                    f"Could not find signals {x_signal=}, {y_signal=} and {r_signal=} in {df.columns}"
                )
                continue
            # Apply transformations
            if use_reference:
                df[y_signal] /= df[r_signal]
            if use_log:
                df[y_signal] = np.log(df[y_signal])
            if use_invert:
                df[y_signal] *= -1
            if use_grad:
                df[y_signal] = np.gradient(df[y_signal], df[x_signal])
            series = pd.Series(df[y_signal].values, index=df[x_signal].values)
            dfs[run.uid] = series
        return dfs

    async def export_runs(self, filenames: Sequence[str], formats: Sequence[str]):
        for filename, run, format in zip(filenames, self.selected_runs, formats):
            await run.export(filename, format=format)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
