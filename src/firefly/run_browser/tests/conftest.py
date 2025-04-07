import re
from urllib.parse import parse_qs, urlparse

import httpx
import pandas as pd
import pytest
from pytest_httpx import IteratorStream
from tiled.serialization.table import serialize_arrow


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


@pytest.fixture()
def tiled_api(httpx_mock):
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
        url="http://localhost:8000/api/v1/search/scans%2Fscan1/",
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
        url="http://localhost:8000/api/v1/metadata/scans%2Fscan1%2Fprimary",
        json=md_to_json({}),
        is_reusable=True,
        is_optional=True,
    )
    httpx_mock.add_response(
        url=re.compile(
            "http://localhost:8000/api/v1/metadata/scans%2F[-a-z0-9]+%2Fprimary%2Finternal%2Fevents"
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
            "http://localhost:8000/api/v1/table/full/scans%2F[-a-z0-9]+%2Fprimary%2Finternal%2Fevents"
        ),
        stream=IteratorStream(
            [
                serialize_arrow(
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
