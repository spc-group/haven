import re
from urllib.parse import parse_qs, urlparse

import httpx
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from pytest_httpx import IteratorStream
from tiled.adapters.dataframe import DataFrameAdapter
from tiled.adapters.mapping import MapAdapter
from tiled.adapters.xarray import DatasetAdapter
from tiled.client import from_context_async
from tiled.client.context import Context
from tiled.serialization.table import serialize_arrow
from tiled.server.app import build_app
from tiled.utils import APACHE_ARROW_FILE_MIME_TYPE


def md_to_json(metadata):
    response = {"data": {"attributes": {"metadata": metadata}}}
    return response


def distinct_fields(request: httpx.Request):
    queries = parse_qs(urlparse(str(request.url)).query)["metadata"]
    md = {
        "start.plan_name": [
            {"value": "scan", "count": None},
            {"value": "real_scan", "count": None},
        ],
        "start.sample_name": [
            {"value": "air", "count": None},
            {"value": "xenonite", "count": None},
        ],
        "start.sample_formula": [
            {"value": "N2", "count": None},
            {"value": "Xe8", "count": None},
        ],
        "start.scan_name": [
            {"value": "pristine", "count": None},
            {"value": "fully charged", "count": None},
        ],
        "start.edge": [
            {"value": "N-L3", "count": None},
            {"value": "Xe-K", "count": None},
        ],
        "stop.exit_status": [
            {"value": "success", "count": None},
            {"value": "disaster", "count": None},
        ],
        "start.proposal_id": [
            {"value": "1", "count": None},
            {"value": "2", "count": None},
        ],
        "start.esaf_id": [
            {"value": "999", "count": None},
            {"value": "998", "count": None},
        ],
        "start.beamline_id": [
            {"value": "255-ID-X", "count": None},
            {"value": "255-ID-Z", "count": None},
        ],
    }
    md = {key: fields for key, fields in md.items() if key in queries}
    return httpx.Response(
        status_code=200,
        json={"metadata": md},
    )


tree = MapAdapter(
    {
        "85573831-f4b4-4f64-b613-a6007bf03a8d": MapAdapter(
            {
                "streams": MapAdapter(
                    {
                        "baseline": MapAdapter({}),
                        "primary": MapAdapter(
                            {
                                "internal": DataFrameAdapter.from_pandas(
                                    pd.DataFrame(
                                        {
                                            "x": 1 * np.ones(10),
                                            "y": 2 * np.ones(10),
                                            "z": 3 * np.ones(10),
                                        }
                                    ),
                                    npartitions=3,
                                ),
                            },
                            metadata={
                                "data_keys": {
                                    "I0-net_count": {
                                        "dtype": "number",
                                    },
                                    "ge_8element": {},
                                    "ge_8element-deadtime_factor": {},
                                    "energy_energy": {},
                                },
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
                            },
                        ),
                    }
                ),
            },
            metadata={
                "start": {
                    "uid": "85573831-f4b4-4f64-b613-a6007bf03a8d",
                    "hints": {
                        "dimensions": [
                            [["aerotech_vert"], "primary"],
                            [["aerotech_horiz"], "primary"],
                        ],
                    },
                    "plan_name": "scan",
                    "beamline_id": "25-ID-C",
                    "sample_name": "Miso",
                    "sample_formula": "Ms",
                    "scan_name": "Dinner",
                    "proposal_id": "000001",
                    "esaf_id": "123456",
                },
                "stop": {
                    "exit_status": "success",
                },
            },
        ),
        "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f": MapAdapter(
            {
                "streams": MapAdapter(
                    {
                        "primary": MapAdapter(
                            {
                                "internal": DataFrameAdapter.from_pandas(
                                    pd.DataFrame(
                                        {
                                            "x": 1 * np.ones(10),
                                            "y": 2 * np.ones(10),
                                            "z": 3 * np.ones(10),
                                        }
                                    ),
                                    npartitions=3,
                                ),
                            },
                            metadata={
                                "data_keys": {
                                    "It-mcs-scaler-channels-3-net_count": {
                                        "dtype": "number",
                                    }
                                },
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
                            },
                        ),
                    }
                ),
            },
            metadata={
                "start": {
                    "uid": "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f",
                    "hints": {
                        "dimensions": [
                            [["aerotech_vert"], "primary"],
                            [["aerotech_horiz"], "primary"],
                        ],
                    },
                    "plan_name": "xafs_scan",
                    "edge": "Ni-K",
                },
                "stop": {
                    "exit_status": "success",
                },
            },
        ),
        "xarray_run": MapAdapter(
            {
                "streams": MapAdapter(
                    {
                        "primary": DatasetAdapter.from_dataset(
                            xr.Dataset(
                                {
                                    "I0-net_count": ("mono-energy", [200, 300, 250]),
                                    "It-net_count": ("mono-energy", [200, 300, 250]),
                                    "other_signal": ("mono-energy", [10, 122, 13345]),
                                    "mono-energy": ("mono-energy", [0, 1, 2]),
                                }
                            ),
                        ),
                    },
                ),
            },
            metadata={
                "start": {
                    "uid": "xarray_run",
                },
            },
        ),
    }
)


@pytest.fixture()
async def tiled_client():
    async with Context.from_app(build_app(tree), awaitable=True) as context:
        client = await from_context_async(context)
        yield client


@pytest.fixture()
def old_tiled_api(httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:8000/api/v1/search/",
        json={
            "data": [
                {"id": "scans"},
                {"id": "testing"},
            ],
            "links": {"next": None},
        },
        is_optional=True,
    )
    httpx_mock.add_callback(
        url=re.compile(
            r"http://localhost:8000/api/v1/distinct/scans\?metadata=[a-z.]+"
        ),
        callback=distinct_fields,
        is_reusable=True,
        is_optional=True,
    )
    httpx_mock.add_response(
        url="http://localhost:8000/api/v1/search/scans%2Fscan1%2Fstreams/",
        json={
            "data": [
                {"id": "primary"},
                {"id": "baseline"},
            ],
            "links": {"next": None},
        },
        is_reusable=True,
        is_optional=True,
    )
    httpx_mock.add_response(
        url="http://localhost:8000/api/v1/metadata/scans%2Fscan1",
        json=md_to_json(
            {
                "start": {"uid": "scan1"},
            }
        ),
        is_reusable=True,
        is_optional=True,
    )
    httpx_mock.add_response(
        url=re.compile(r"^http://localhost:8000/api/v1/search/scans/($|\?)"),
        json={
            "data": [{"id": "scan1"}],
            "links": {"next": None},
        },
        is_reusable=True,
        is_optional=True,
    )
    httpx_mock.add_response(
        url="http://localhost:8000/api/v1/metadata/scans%2Fscan1%2Fstreams%2Fprimary",
        json=md_to_json({}),
        is_reusable=True,
        is_optional=True,
    )
    httpx_mock.add_response(
        url=re.compile(
            "http://localhost:8000/api/v1/metadata/scans%2F[-a-z0-9]+%2Fstreams%2Fprimary%2Finternal"
        ),
        json={
            "data": {
                "id": "events",
                "attributes": {
                    "ancestors": [
                        "scans",
                        "a21b0ee2-6a06-4c7c-b96b-0dab9b0eef75",
                        "primary",
                        "internal",
                    ],
                    "metadata": {
                        "uid": "ba1bfc01-9382-4f78-8e19-513fa0e217fd",
                    },
                    "structure_family": "table",
                    # "structure": {
                    #     "data_type": {
                    #         "endianness": "little",
                    #         "kind": "u",
                    #         "itemsize": 4,
                    #         "dt_units": None
                    #     },
                    #     "chunks": [
                    #         [1] * 51,
                    #         [514],
                    #         [1030]
                    #     ],
                    #     "shape": [
                    #         51,
                    #         514,
                    #         1030
                    #     ],
                    #     "dims": None,
                    #     "resizable": False
                    # },
                },
            },
        },
        is_reusable=True,
        is_optional=True,
    )
    httpx_mock.add_response(
        url=re.compile(
            "http://localhost:8000/api/v1/table/full/scans%2F[-a-z0-9]+%2Fstreams%2Fprimary%2Finternal"
        ),
        stream=IteratorStream(
            [
                serialize_arrow(
                    APACHE_ARROW_FILE_MIME_TYPE,
                    pd.DataFrame(
                        {
                            "seq_num": [1, 2, 3],
                            "I0": [2000, 2013, 1998],
                        }
                    ),
                    metadata={},
                )
            ]
        ),
        is_reusable=True,
        is_optional=True,
    )

    # httpx_mock.add_response(
    #     url="http://localhost:8000/api/v1/table/full/scans%2Fscan1%2Fprimary%2Finternal%2Fevents",
    #     json={
    #         "seq_num": [1, 2, 3],
    #         "I0": [2000, 2013, 1998],
    #     },
    #     is_reusable=True,
    #     is_optional=True,
    # )
