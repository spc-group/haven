from pathlib import Path

import pytest

from haven import bss


beamlines = [
    {
        "beamlineNum": 217,
        "beamlineId": "25-ID-C",
        "beamlineName": "Advanced Spectroscopy",
    },
]

runs = [
    {
        "runId": 467,
        "runName": "2024-3",
        "startTime": "2024-10-01T00:00:00-05:00",
        "endTime": "2024-12-19T08:00:00-06:00",
        "version": 0
    },
    {
        "runId": 486,
        "runName": "2025-1",
        "startTime": "2024-05-06T08:00:00-05:00",
        "endTime": "2024-10-01T00:00:00-05:00",
        "version": 0
    },
    {
        "runId": 506,
        "runName": "2025-3",
        "startTime": "2025-09-05T15:06:00-05:00",
    "endTime": "2026-01-16T15:07:00-06:00",
    "version": 0
  }
]


base_uri = "https://beam-api-dev.aps.anl.gov:80/beamline-scheduling/sched-api"


@pytest.fixture()
def mock_api(httpx_mock):
    pass


async def test_get_beamlines(mock_api, httpx_mock):
    # List of beamlines
    httpx_mock.add_response(url="/".join([base_uri, "beamline", "findAllActiveBeamlines"]), json=beamlines)
    api = bss.BSSApi()
    beamlines_ = await api.beamlines()
    assert len(beamlines_) == 1
    names = {bl.name for bl in beamlines_}
    assert names == {"Advanced Spectroscopy"}


async def test_get_runs(mock_api, httpx_mock):
    # List of runs
    httpx_mock.add_response(url="/".join([base_uri, "run", "getAllRuns"]), json=runs)
    api = bss.BSSApi()
    runs_ = await api.runs()
    assert len(runs_) == 3
    names = {run.name for run in runs_}
    assert names == {"2024-3", "2025-1", "2025-3"}
    
