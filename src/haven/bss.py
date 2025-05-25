import dataclasses
from typing import Any, Mapping, Sequence
import json
import datetime as dt

import httpx
import stamina


# @dataclasses.dataclass(frozen=True)
# class Run:
#     run_id: str
#     name: str
#     start: float
#     end: float


# @dataclasses.dataclass(frozen=True)
# class Beamline:
#     number: int
#     beamline_id: str
#     name: str


@dataclasses.dataclass(frozen=True)
class User:
    badge: str
    first_name: str
    last_name: str
    email: str
    is_pi: bool
    institution: str | None


@dataclasses.dataclass(frozen=True)
class Esaf:
    esaf_id: str
    description: str
    sector: str
    title: str
    start: dt.datetime
    end: dt.datetime
    status: str
    users: list[User]


@dataclasses.dataclass(frozen=True)
class Proposal:
    title: str
    proposal_id: str
    users: list[User]
    start: dt.datetime
    end: dt.datetime
    duration: dt.timedelta
    mail_in: bool
    proprietary: bool


class BSSParser:
    def esafs(self, json_data: str) -> list[Esaf]:
        data = json.loads(json_data)
        esafs_ = [self._esaf(datum) for datum in data]
        return esafs_

    def esaf(self, json_data: str) -> Esaf:
        data = json.loads(json_data)
        return self._esaf(data)

    def _esaf(self, data: Mapping[str, Any]) -> Esaf:
        # Scheduling dates
        dt_format = "%Y-%m-%d %H:%M:%S"
        start = dt.datetime.strptime(data['experimentStartDate'], dt_format)
        end = dt.datetime.strptime(data['experimentEndDate'], dt_format)
        # Users
        users = [User(
            badge=user['badge'],
            first_name=user['firstName'],
            last_name=user['lastName'],
            email=user['email'],
            is_pi=user['piFlag'] == "Yes",
            institution=None,
        ) for user in data['experimentUsers']]
        # Create the ESAF
        return Esaf(
            title=data['esafTitle'],
            description=data['description'],
            esaf_id=str(data['esafId']),
            sector=data['sector'],
            status=data['esafStatus'],
            start=start,
            end=end,
            users=users,
        )

    def proposals(self, json_data: str) -> list[Proposal]:
        data = json.loads(json_data)
        return [self._proposal(datum) for datum in data]

    def proposal(self, json_data: str) -> Proposal:
        data = json.loads(json_data)
        return self._proposal(data)
    
    def _proposal(self, data: Mapping[str, Any]) -> Proposal:
        # Scheduling dates
        # dt_format = "%Y-%m-%d %H:%M:%S"
        start = dt.datetime.fromisoformat(data['startTime'])
        end = dt.datetime.fromisoformat(data['endTime'])
        duration = dt.timedelta(seconds=data['duration'])
        # Create users for the proposal
        users = [
            User(
                badge=user_data['badge'],
                first_name=user_data['firstName'],
                last_name=user_data['lastName'],
                is_pi=user_data['piFlag'],
                email=None,
                institution=user_data["institution"],

            )
            for user_data in data['experimenters']
        ]
        # Create the proposal itself
        return Proposal(
            title=data["title"],
            proposal_id=f"{data['id']:07}",
            users = users,
            start=start,
            end=end,
            duration=duration,
            mail_in=(data['mailInFlag'] == "Yes"),
            proprietary=(data['proprietaryFlag'] == "Yes"),
        )
    
    # def beamlines(self, json_data: str) -> list[Beamline]:
    #     run_data = json.loads(json_data)
    #     beamlines = [
    #         Beamline(
    #             beamline_id=beamline["beamlineId"],
    #             number=beamline['beamlineNum'],
    #             name=beamline['beamlineName'],
    #         )
    #         for beamline in run_data
    #     ]
    #     return beamlines

    # def runs(self, json_data: str) -> list[Run]:
    #     run_data = json.loads(json_data)
    #     # Translate keys to match the dataclass
    #     runs = [
    #         Run(
    #             run_id=run["runId"],
    #             name=run["runName"],
    #             start=dt.datetime.fromisoformat(run["startTime"]),
    #             end=dt.datetime.fromisoformat(run["endTime"]),
    #         )
    #         for run in run_data
    #     ]
    #     return runs


class BSSApi:
    """Client for the APS data management REST API.

    REST API Endpoints
    ==================

    | Endpoint                           | Meaning                                         |
    |------------------------------------+-------------------------------------------------|
    | /dm/proposals/2023-1/25-ID-C       | Array of proposals at 25-ID-C for 2023-1 cycle. |
    | /dm/esafsBySectorAndYear/20/2020   | ESAFs for sector 20 in year 2020.               |
    | /dm/proposals/2022-2/20-BM-B/12345 | Propsal # 12345 during 2022-2 cycle at 20-BM-B  |
    | /dm/esafs/12345                    | ESAF #12345                                     |

    """

    _client: httpx.AsyncClient | None = None
    base_uri: str = "https://xraydtn02.xray.aps.anl.gov:11336/dm"
    parser = BSSParser()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_uri)
        return self._client

    @stamina.retry(on=httpx.HTTPError, attempts=3)
    async def _http_get(self, url: str) -> httpx.Response:
        return await self.client.get(url)

    # async def beamlines(self) -> list[Beamline]:
    #     """Load the activate beamlines at the APS."""
    #     response = await self._http_get("/beamline/findAllActiveBeamlines")
    #     return self.parser.beamlines(response.text)

    # async def runs(self) -> list[Run]:
    #     """Load the operating runs at the APS (e.g. 2025-3)."""
    #     response = await self._http_get("/run/getAllRuns")
    #     return self.parser.runs(response.text)

    async def esafs(self, sector: str, year: str) -> list[Esaf]:
        """Load the ESAF's for the given *sector* and *year*."""
        response = await self._http_get(f"esafsBySectorAndYear/{sector}/{year}")
        return self.parser.esafs(response.text)

    async def esaf(self, esaf_id: str) -> Esaf:
        """Load the ESAF's for the given *sector* and *year*."""
        response = await self._http_get(f"esafs/{esaf_id}")
        return self.parser.esaf(response.text)


    async def proposals(self, cycle: str, beamline: str):
        """Load the proposals for a given *beamline* during a given *cycle*."""
        response = await self._http_get(f"proposals/{cycle}/{beamline}")
        return self.parser.proposals(response.text)

    async def proposal(self, proposal_id: str, cycle: str, beamline: str):
        """Load the given proposal on a given *beamline* during a given *cycle*."""
        response = await self._http_get(f"proposals/{cycle}/{beamline}/{proposal_id}")
        return self.parser.proposal(response.text)
    
