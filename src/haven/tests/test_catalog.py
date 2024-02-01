import logging
from unittest.mock import MagicMock

import pandas as pd
import numpy as np
import pandas as pd
import pytest
from pyqtgraph import PlotItem, PlotWidget, ImageView, ImageItem
from qtpy.QtCore import Qt
from tiled import queries
from tiled.adapters.mapping import MapAdapter
from tiled.adapters.xarray import DatasetAdapter
from tiled.client import Context, from_context
from tiled.server.app import build_app


from haven.catalog import Catalog, CatalogScan


# Some mocked test data
run1 = pd.DataFrame(
    {
        "energy_energy": np.linspace(8300, 8400, num=100),
        "It_net_counts": np.abs(np.sin(np.linspace(0, 4 * np.pi, num=100))),
        "I0_net_counts": np.linspace(1, 2, num=100),
    }
)

grid_scan = pd.DataFrame(
    {
        'CdnIPreKb': np.linspace(0, 104, num=105),
        "It_net_counts": np.linspace(0, 104, num=105),
        "aerotech_horiz": np.linspace(0, 104, num=105),
        "aerotech_vert": np.linspace(0, 104, num=105),
    }
        
)

hints = {
    "energy": {"fields": ["energy_energy", "energy_id_energy_readback"]},
}

bluesky_mapping = {
    "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(run1.to_xarray()),
                },
                metadata={"descriptors": [{"hints": hints}]},
            ),
        },
        metadata={
            "plan_name": "xafs_scan",
            "start": {
                "plan_name": "xafs_scan",
                "uid": "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f",
                "hints": {"dimensions": [[["energy_energy"], "primary"]]},
            },
        },
    ),
    "9d33bf66-9701-4ee3-90f4-3be730bc226c": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(run1.to_xarray()),
                },
                metadata={"descriptors": [{"hints": hints}]},
            ),
        },
        metadata={
            "start": {
                "plan_name": "rel_scan",
                "uid": "9d33bf66-9701-4ee3-90f4-3be730bc226c",
                "hints": {"dimensions": [[["pitch2"], "primary"]]},
            }
        },
    ),
    # 2D grid scan map data
    "85573831-f4b4-4f64-b613-a6007bf03a8d": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(grid_scan.to_xarray()),
                }, metadata={
                    "descriptors": [{"hints": {'Ipreslit': {'fields': ['Ipreslit_net_counts']},
                                               'CdnIPreKb': {'fields': ['CdnIPreKb_net_counts']},
                                               'I0': {'fields': ['I0_net_counts']},
                                               'CdnIt': {'fields': ['CdnIt_net_counts']},
                                               'aerotech_vert': {'fields': ['aerotech_vert']},
                                               'aerotech_horiz': {'fields': ['aerotech_horiz']},
                                               'Ipre_KB': {'fields': ['Ipre_KB_net_counts']},
                                               'CdnI0': {'fields': ['CdnI0_net_counts']},
                                               'It': {'fields': ['It_net_counts']}}}]
                }),
        },
        metadata={
            "start": {
                "plan_name": "grid_scan",
                "uid": "85573831-f4b4-4f64-b613-a6007bf03a8d",
                "hints": {
                    'dimensions': [[['aerotech_vert'], 'primary'],
                                   [['aerotech_horiz'], 'primary']],
                    'gridding': 'rectilinear'
                },
                "shape": [5, 21],
                "extents": [[-80, 80], [-100, 100]],
            },
        },
    ),
}


mapping = {
    "255id_testing": MapAdapter(bluesky_mapping),
}

tree = MapAdapter(mapping)


@pytest.fixture(scope="module")
def client():
    app = build_app(tree)
    with Context.from_app(app) as context:
        client = from_context(context)
        yield client["255id_testing"]


@pytest.fixture(scope="module")
def catalog(client):
    return Catalog(client=client)


@pytest.fixture()
def scan(client):
    uid = "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f"
    return CatalogScan(client[uid])


@pytest.fixture()
def grid_scan(client):
    uid = "85573831-f4b4-4f64-b613-a6007bf03a8d"
    return CatalogScan(client[uid])



@pytest.mark.asyncio
async def test_client_fixture(client):
    """Does the client fixture load without stalling the test runner?"""


@pytest.mark.asyncio
async def test_load_scan(catalog):
    """Check that scans can be loaded from the catalog."""
    uid = "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f"
    scan = await catalog[uid]
    assert isinstance(scan, CatalogScan)


@pytest.mark.asyncio
async def test_dataframe(scan):
    """Check that the catalogscan can produce a pandas dataframe."""
    df = await scan.to_dataframe()
    assert isinstance(df, pd.DataFrame)

@pytest.mark.asyncio
async def test_load_nd_data(grid_scan):
    """Check that the catalog scan can convert e.g. grid_scan results."""
    arr = await grid_scan["It_net_counts"]
    assert arr.ndim == 2
    assert arr.shape == (5, 21)


@pytest.mark.asyncio
async def test_distinct(catalog, client):
    distinct = client.distinct("plan_name")
    assert await catalog.distinct("plan_name") == distinct

@pytest.mark.asyncio
async def test_search(catalog, client):
    """Make sure we can query to database properly."""
    query = queries.Regex("plan_name", "xafs_scan")
    expected = client.search(query)
    response = await catalog.search(query)
    assert len(expected) == len(response)

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
