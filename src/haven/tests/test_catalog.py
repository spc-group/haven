import re
import io

import httpx
import numpy as np
import pytest
from pytest_httpx import IteratorStream
from tiled import queries

from haven.catalog import CatalogScan, unsnake, Catalog, resolve_uri, deserialize_array


run_metadata_re = re.compile(r"^http://localhost:8000/api/v1/metadata/([a-z]+)%2F([-a-z0-9]+)$")


def run_metadata(request: httpx.Request):
    url = str(request.url)
    catalog, uid = run_metadata_re.match(url).groups()
    md = {
        "data": {
            "attributes": {
                "structure_family": "container",
                "specs": [
                    {
                        "name": "BlueskyRun",
                        "version": "1.0"
                    }
                ],
                "metadata": {
                    "start": {
                        "uid": uid,
                        "hints": {
                            "dimensions": [
                                [["aerotech_vert"], "primary"],
                                [["aerotech_horiz"], "primary"],
                            ],
                        }
                    }
                }
            }
        }
    }
    return httpx.Response(
        status_code=200, json=md,
    )


@pytest.fixture()
def run(httpx_mock):
    httpx_mock.add_callback(
        url=run_metadata_re,
        callback=run_metadata,
        is_reusable=True,
        is_optional=True,
    )
    client = httpx.AsyncClient(base_url="http://localhost:8000/api/v1/")
    return CatalogScan(path="scans/518edf43-7370-4670-8e61-e1e18a8152cf", client=client)


@pytest.fixture()
def catalog():
    return Catalog(uri="http://localhost:8000/", path="scans")


@pytest.fixture()
def grid_scan(tiled_client):
    uid = "85573831-f4b4-4f64-b613-a6007bf03a8d"
    return CatalogScan(tiled_client["255id_testing"][uid])


def test_unsnake():
    # Make a snaked array
    arr = np.arange(27).reshape((3, 3, 3))
    snaked = np.copy(arr)
    snaked[::2] = snaked[::2, ::-1]
    snaked[:, ::2] = snaked[:, ::2, ::-1]
    # Do the unsnaking
    unsnaked = unsnake(snaked, [False, True, True])
    # Check the result
    np.testing.assert_equal(arr, unsnaked)


def test_load_scan(catalog):
    """Check that scans can be loaded from the catalog."""
    # Do the API call
    uid = "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f"
    scan = catalog[uid]
    assert isinstance(scan, CatalogScan)


@pytest.mark.skip(reason="Make sure we need this first.")
@pytest.mark.asyncio
async def test_load_nd_data(grid_scan):
    """Check that the catalog scan can convert e.g. grid_scan results."""
    arr = await grid_scan["It_net_counts"]
    assert arr.ndim == 2
    assert arr.shape == (5, 21)


@pytest.mark.asyncio
async def test_distinct(catalog, httpx_mock):
    distinct = {
        "start.plan_name": [
            {"value": "scan", "count": None},
            {"value": "real_scan", "count": None},
        ],
    }
    httpx_mock.add_response(
        json={"metadata": distinct},
        url="http://localhost:8000/api/v1/distinct/scans?metadata=plan_name",
    )
    assert [run async for run in catalog.distinct("plan_name")] == [distinct]


@pytest.fixture()
def search_api(httpx_mock):
    params = {
        "sort": "-name",
        "filter[regex][condition][key]": ["plan_name"],
        "filter[regex][condition][pattern]": ["xafs_scan"],
        "filter[regex][condition][case_sensitive]": [True],
    }
    httpx_mock.add_response(
        json={
            "data": [{"id": "scan1"}],
            "links": {
                "next": "http://localhost:8000/api/v1/search/scans/pt2",
            },
        },
        url=httpx.URL(
            "http://localhost:8000/api/v1/search/scans/",
            params=params,
        ),
    )
    # Include a second API call to make sure pagination works
    httpx_mock.add_response(
        json={
            "data": [{"id": "scan2"}],
            "links": {
                "next": None,
            },
        },
        url=httpx.URL(
            "http://localhost:8000/api/v1/search/scans/pt2",
            params=params,
        ),
    )



@pytest.mark.asyncio
async def test_catalog_runs(catalog, search_api):
    """Make sure we can query to database properly."""
    # Run the gnerator
    query = queries.Regex("plan_name", "xafs_scan")
    runs = catalog.runs(queries=[query], sort=["-name"])
    runs = [run async for run in runs]
    # Make sure the results are right
    assert len(runs) == 2


@pytest.mark.skip("Come back to this one")
async def test_run_pages(catalog, search_api):
    """Check that we can get pages of runs in a generator."""
    pages = [page async for page in catalog.run_pages]
    assert len(pages) == 2


async def test_hints(run, httpx_mock):
    # Respond with plan hints
    # httpx_mock.add_response(
    #     json={
    #         "data": {
    #             "attributes": {
    #                 "metadata": {
    #                     "start": {
    #                         "hints": {
    #                             "dimensions": [
    #                                 [["aerotech_vert"], "primary"],
    #                                 [["aerotech_horiz"], "primary"],
    #                             ],
    #                         }
    #                     }
    #                 }
    #             }
    #         }
    #     }
    # )
    # Respond with stream hints
    httpx_mock.add_response(
        json={
            "data": {
                "attributes": {
                    "metadata": {
                        "hints": {
                            "Ipreslit": {"fields": ["Ipreslit_net_counts"]},
                            "CdnIPreKb": {"fields": ["CdnIPreKb_net_counts"]},
                            "I0": {"fields": ["I0_net_counts"]},
                            "CdnIt": {"fields": ["CdnIt_net_counts"]},
                            "aerotech_vert": {"fields": ["aerotech_vert"]},
                            "aerotech_horiz": {"fields": ["aerotech_horiz"]},
                            "Ipre_KB": {"fields": ["Ipre_KB_net_counts"]},
                            "CdnI0": {"fields": ["CdnI0_net_counts"]},
                            "It": {"fields": ["It_net_counts"]},
                        },
                    }
                }
            }
        }
    )
    ihints, dhints = await run.hints()
    assert ihints == ["aerotech_vert", "aerotech_horiz"]
    assert dhints == [
        "Ipreslit_net_counts",
        "CdnIPreKb_net_counts",
        "I0_net_counts",
        "CdnIt_net_counts",
        "aerotech_vert",
        "aerotech_horiz",
        "Ipre_KB_net_counts",
        "CdnI0_net_counts",
        "It_net_counts",
    ]


async def test_metadata(run):
    assert (await run.metadata)['start']['uid'] == "518edf43-7370-4670-8e61-e1e18a8152cf"
    assert (await run.uid) == "518edf43-7370-4670-8e61-e1e18a8152cf"


def test_resolve_uri():
    assert resolve_uri("http://localhost:8000/") == "http://localhost:8000/api/v1"
    assert resolve_uri("http://localhost:8000/api/") == "http://localhost:8000/api/v1"
    assert resolve_uri("http://localhost:8000/api/v1/") == "http://localhost:8000/api/v1"


def test_deserialize_array():
    arr = np.arange(10, dtype="uint32").reshape(2, 5)
    buff = arr.tobytes()
    deserialized = deserialize_array(buff, {
        "data_type": {
            "endianness": "little",
            "kind": "u",
            "itemsize": 4,
            "dt_units": None
        },
        "chunks": [
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [514],
            [1030]
        ],
        "shape": [2, 5],
        "dims": None,
        "resizable": False
    })
    np.testing.assert_array_equal(deserialized, arr)


async def test_formats(run, httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:8000/api/v1/",
        json={
            "formats": {
                "container": ["application/x-nexus"],
                "BlueskyRun": ["text/tab-separated-values"],
            },
        }
    )
    assert await run.formats() == ["application/x-nexus", "text/tab-separated-values"]


async def test_export(run, httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:8000/api/v1/container/full/scans%2F518edf43-7370-4670-8e61-e1e18a8152cf?format=text%2Ftab-separate-values",
        stream=IteratorStream([b"hello\n", b"world\n"]),
    )
    buff = io.BytesIO()
    await run._export(buff, format="text/tab-separate-values")
    buff.seek(0)
    streamed = buff.read()
    assert streamed == b"hello\nworld\n"

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
