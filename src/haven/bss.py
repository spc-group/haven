import datetime as dt
import json
from base64 import b64encode
from typing import Any, Mapping

import httpx
import stamina
from pydantic import BaseModel

__all__ = ["Esaf", "Proposal", "User", "BssApi"]


class User(BaseModel):
    badge: str
    first_name: str
    last_name: str
    email: str | None
    is_pi: bool
    institution: str | None


class Esaf(BaseModel):
    esaf_id: str
    description: str
    sector: str
    title: str
    start: dt.datetime
    end: dt.datetime
    status: str
    users: list[User]


class Proposal(BaseModel):
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
        start = dt.datetime.strptime(data["experimentStartDate"], dt_format)
        end = dt.datetime.strptime(data["experimentEndDate"], dt_format)
        # Users
        users = [
            User(
                badge=user["badge"],
                first_name=user["firstName"],
                last_name=user["lastName"],
                email=user.get("email"),
                is_pi=user["piFlag"] == "Yes",
                institution=None,
            )
            for user in data["experimentUsers"]
        ]
        # Create the ESAF
        return Esaf(
            title=data["esafTitle"],
            description=data["description"],
            esaf_id=str(data["esafId"]),
            sector=data["sector"],
            status=data["esafStatus"],
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
        start = dt.datetime.fromisoformat(data["startTime"])
        end = dt.datetime.fromisoformat(data["endTime"])
        duration = dt.timedelta(seconds=data["duration"])
        # Create users for the proposal
        users = [
            User(
                badge=user_data["badge"],
                first_name=user_data["firstName"],
                last_name=user_data["lastName"],
                is_pi=user_data["piFlag"],
                email="",
                institution=user_data["institution"],
            )
            for user_data in data["experimenters"]
        ]
        # Create the proposal itself
        return Proposal(
            title=data["title"],
            proposal_id=f"{data['id']:07}",
            users=users,
            start=start,
            end=end,
            duration=duration,
            mail_in=(data["mailInFlag"] == "Yes"),
            proprietary=(data["proprietaryFlag"] == "Yes"),
        )


def encode(string: str) -> bytes:
    """Double-base64 encoded version of the input *string*."""
    return b64encode(b64encode(string.encode()))


class DMAuth(httpx.Auth):

    def __init__(self, username: str, password: str, base_uri: str):
        self.username = username
        self.password = password
        self.base_uri = base_uri

    def auth_flow(self, request: httpx.Request):
        # Try the original request first, maybe we don't need to log in
        response = yield request
        if response.status_code == 401:
            # Make an extra login request to get the session cookie
            login_url = f"{self.base_uri}/login"
            response = yield httpx.Request(
                method="POST",
                url=login_url,
                data={"username": self.username, "password": self.password},
            )
            # Authentication was successful, try the original request again
            if response.status_code == 200:
                request.headers["cookie"] = response.headers["set-cookie"]
                yield request
            else:
                return response


def raise_for_status(response: httpx.Response) -> httpx.Response:
    """Raises an exception if the response did not complete successfully.

    Similar to the behavior of httpx.Response.raise_for_status, but
    also accounts for situations where the dm API returns a 200 status
    code, but the response content contains error information.

    """
    response = response.raise_for_status()
    content = response.json()
    if "errorCode" not in content and "errorMessage" not in content:
        # Everything is fine, just send the response on
        return response
    error_code = content.get("errorCode", "??")
    error_message = content.get("errorMessage", "Unknown error")
    raise httpx.HTTPStatusError(
        f"{error_message} ({error_code})", response=response, request=response.request
    )


class BssApi:
    """Client for the APS data management REST API.

    REST API Endpoints
    ==================

    - /dm/esaf/stationEsafs/{station_name*}/{beamline_name*}?year={year}
    - /dm/esaf/stationEsafsById/{station_name*}/{esaf_id}
    - /dm/bss/stationProposals/{station_name*}/{beamline_name*}?runName={run}
    - /dm/bss/stationProposalsById/{station_name*}/{proposal_id}?runName={run}

    * double base64 encoded bytestring
    """

    _client: httpx.AsyncClient
    base_uri: str
    parser = BSSParser()
    auth: httpx.Auth

    def __init__(self, username: str, password: str, station_name: str, uri: str):
        """*username*, *password*, and *station_name* are all assigned by the
        data management group.

        """
        # Standardize the host URI
        uri = uri.rstrip("/")
        if uri.split("/")[-1] != "dm":
            # Add the 'dm' prefix for paths
            uri = f"{uri}/dm"
        self.base_uri = uri
        self.auth = DMAuth(username=username, password=password, base_uri=self.base_uri)
        self.station_name = encode(station_name)

    @property
    def client(self) -> httpx.AsyncClient:
        if not hasattr(self, "_client"):
            # API certificates are not signed by a trusted local issuer
            # If that changes, set `verify=True`
            self._client = httpx.AsyncClient(
                base_url=self.base_uri, auth=self.auth, verify=False
            )
        return self._client

    @stamina.retry(on=httpx.HTTPError, attempts=3)
    async def _http_get(
        self, url: str, params: Mapping | None = None
    ) -> httpx.Response:
        # Clean up the URL in case there are missing parameters
        url = url.removesuffix("/b''")
        response = await self.client.get(url, params=params)
        return raise_for_status(response)

    async def esafs(self, beamline: str = "", year: str | None = None) -> list[Esaf]:
        """Load the ESAF's for the given *beamline* and *year*."""
        url = f"esaf/stationEsafs/{self.station_name!r}/{encode(beamline)!r}"
        params = {"year": year} if year else None
        response = await self._http_get(url, params=params)
        return self.parser.esafs(response.text)

    async def esaf(self, esaf_id: str) -> Esaf:
        """Load the ESAF's for the given *sector* and *year*."""
        url = f"esaf/stationEsafsById/{self.station_name!r}/{esaf_id}"
        response = await self._http_get(url)
        return self.parser.esaf(response.text)

    async def proposals(self, beamline: str = "", cycle: str | None = None):
        """Load the proposals for a given *beamline* during a given *cycle*."""
        url = f"bss/stationProposals/{self.station_name!r}/{encode(beamline)!r}"
        params = {"runName": cycle} if cycle else None
        response = await self._http_get(url, params=params)
        return self.parser.proposals(response.text)

    async def proposal(self, proposal_id: str, cycle: str | None = None):
        """Load the given proposal on a given *beamline* during a given *cycle*."""
        url = f"bss/stationProposalsById/{self.station_name!r}/{proposal_id}"
        params = {"runName": cycle} if cycle else None
        response = await self._http_get(url, params=params)
        return self.parser.proposal(response.text)


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
