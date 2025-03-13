import re

import pytest


def md_to_json(metadata):
    response = {"data": {"attributes": {"metadata": metadata}}}
    return response


@pytest.fixture()
def tiled_api(httpx_mock):
    httpx_mock.add_response(
        url="http://localhost:8000/api/v1/search",
        json={
            "data": [
                {"id": "scans"},
                {"id": "testing"},
            ],
            "links": {"next": None},
        },
        is_optional=True,
    )
    httpx_mock.add_response(
        url="http://localhost:8000/api/v1/distinct/scans",
        json={
            "metadata": {
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
            },
        },
        is_optional=True,
    )
    httpx_mock.add_response(
        url="http://localhost:8000/api/v1/search/scans%2Fscan1",
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
        json=md_to_json({
            "start": {
                "uid": "scan1"
            },
        }),
        is_reusable=True,
        is_optional=True,
    )
    httpx_mock.add_response(
        url=re.compile(r"^http://localhost:8000/api/v1/search/scans($|\?)"),
        json={
            "data": [
                {"id": "scan1"}
            ],
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
        url="http://localhost:8000/api/v1/table/full/scans%2Fscan1%2Fprimary%2Finternal%2Fevents",
        json={
            "seq_num": [1, 2, 3],
            "I0": [2000, 2013, 1998],
        },
        is_reusable=True,
        is_optional=True,
    )
