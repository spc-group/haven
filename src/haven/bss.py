import dataclasses
from typing import Any
import json
import datetime as dt

import httpx
import stamina


@dataclasses.dataclass(frozen=True)
class Run:
    run_id: str
    name: str
    start: float
    end: float


@dataclasses.dataclass(frozen=True)
class Beamline:
    number: int
    beamline_id: str
    name: str


class BSSParser:
    def beamlines(self, json_data: str) -> list[Beamline]:
        run_data = json.loads(json_data)
        beamlines = [
            Beamline(
                beamline_id=beamline["beamlineId"],
                number=beamline['beamlineNum'],
                name=beamline['beamlineName'],
            )
            for beamline in run_data
        ]
        return beamlines

    def runs(self, json_data: str) -> list[Run]:
        run_data = json.loads(json_data)
        # Translate keys to match the dataclass
        runs = [
            Run(
                run_id=run["runId"],
                name=run["runName"],
                start=dt.datetime.fromisoformat(run["startTime"]),
                end=dt.datetime.fromisoformat(run["endTime"]),
            )
            for run in run_data
        ]
        return runs


class BSSApi:
    _client: httpx.AsyncClient | None = None
    base_uri: str = "https://beam-api-dev.aps.anl.gov:80/beamline-scheduling/sched-api"
    parser = BSSParser()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_uri)
        return self._client

    @stamina.retry(on=httpx.HTTPError, attempts=3)
    async def _http_get(self, url: str) -> httpx.Response:
        return await self.client.get(url)

    async def beamlines(self) -> list[Beamline]:
        """Load the activate beamlines at the APS."""
        response = await self._http_get("/beamline/findAllActiveBeamlines")
        return self.parser.beamlines(response.text)

    async def runs(self) -> list[Run]:
        """Load the operating runs at the APS (e.g. 2025-3)."""
        response = await self._http_get("/run/getAllRuns")
        return self.parser.runs(response.text)
