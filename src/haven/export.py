import argparse
import asyncio
import datetime as dt
import re
from pathlib import Path

from tiled import queries
from tiled.client.container import Container
from tqdm.asyncio import tqdm

from haven.catalog import Catalog

extensions = {
    "application/x-nexus": ".hdf",
    "text/tab-separated-values": ".tsv",
}


async def export_run(
    run: Container, *, base_dir: Path, use_xdi: bool = True, use_nexus: bool = True
):
    # Decide on export formats
    valid_formats = await run.formats()
    target_formats = []
    if use_nexus:
        target_formats.append("application/x-nexus")
    if use_xdi:
        target_formats.append(
            "text/x-xdi"
            if "text/x-xdi" in valid_formats
            else "text/tab-separated-values"
        )
    if len(target_formats) == 0:
        return
    # Retrieve needed metadata
    md = await run.metadata
    start_doc = md["start"]
    esaf = start_doc.get("esaf_id", "noesaf")
    pi_name = "nopi"
    start_time = dt.datetime.fromtimestamp(start_doc.get("time"))
    # Decide on how to structure the file storage
    esaf_dir = base_dir / f"{pi_name}-{start_time.strftime('%Y_%m')}-{esaf}"
    sample_name = start_doc.get("sample_name")
    scan_name = start_doc.get("scan_name")
    plan_name = start_doc["plan_name"]
    uid_base = start_doc["uid"].split("-")[0]
    bits = [
        start_time.strftime("%Y%m%d%H%M"),
        sample_name,
        scan_name,
        plan_name,
        uid_base,
    ]
    bits = [bit for bit in bits if bit not in ["", None]]
    base_name = "-".join(bits)
    base_name = re.sub(r"[ ]", "_", base_name)
    base_name = re.sub(r"[/]", "", base_name)
    # Write to disk
    for fmt in target_formats:
        ext = extensions[fmt]
        fp = esaf_dir / f"{base_name}{ext}"
        if fp.exists():
            continue
        # Create the base directory
        esaf_dir.mkdir(parents=True, exist_ok=True)
        # Export files
        await run.export(fp, format=fmt)


def build_queries(
    before: str | None, after: str | None, esaf: str | None, proposal: str | None
) -> list[queries.NoBool]:
    qs = [
        queries.Eq("stop.exit_status", "success"),
    ]
    if after is not None:
        timestamp = dt.datetime.fromisoformat(after).timestamp()
        qs.append(queries.Comparison("ge", "start.time", timestamp))
    if before is not None:
        timestamp = dt.datetime.fromisoformat(before).timestamp()
        qs.append(queries.Comparison("le", "stop.time", timestamp))
    if esaf is not None:
        raise ValueError("ESAF filtering not yet supported")
    if proposal is not None:
        raise ValueError("Proposal filtering not yet supported")
    return qs


async def export_runs(
    base_dir: Path,
    before: str | None,
    after: str | None,
    esaf: str | None,
    proposal: str | None,
    use_xdi: bool,
    use_nexus: bool,
):
    catalog = Catalog("scans", uri="http://fedorov.xray.aps.anl.gov:8020")
    qs = build_queries(before=before, after=after, esaf=esaf, proposal=proposal)
    runs = catalog.runs(queries=qs)
    async for run in tqdm(runs, desc="Exporting", unit="runs"):
        await export_run(run, base_dir=base_dir)


def main():
    parser = argparse.ArgumentParser(
        prog="export-runs",
        description="Export runs from the database as files on disk",
    )
    parser.add_argument(
        "base_dir", help="The base directory for storing files.", type=str
    )
    # Arguments for filtering runs
    parser.add_argument(
        "--before",
        help="Only include runs before this timestamp. E.g. 2025-04-22T8:00:00.",
        type=str,
    )
    parser.add_argument(
        "--after",
        help="Only include runs after this ISO datetime. E.g. 2025-04-22T8:00:00.",
        type=str,
    )
    parser.add_argument("--esaf", help="Export runs with this ESAF ID.", type=str)
    parser.add_argument(
        "--proposal", help="Export runs with this proposal ID.", type=str
    )
    # Arguments for export formats
    parser.add_argument(
        "--nexus",
        help="Export files to HDF files with the NeXus schema",
        action="store_true",
    )
    parser.add_argument(
        "--xdi",
        help="Export files to XDI tab-separated value files.",
        action="store_true",
    )
    args = parser.parse_args()
    # Save each run to disk
    base_dir = Path(args.base_dir)
    do_export = export_runs(
        base_dir=base_dir,
        before=args.before,
        after=args.after,
        esaf=args.esaf,
        proposal=args.proposal,
        use_xdi=args.xdi,
        use_nexus=args.nexus,
    )
    asyncio.run(do_export)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2025, UChicago Argonne, LLC
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
