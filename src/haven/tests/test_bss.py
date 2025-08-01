import httpx
import pytest
import stamina

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
        "version": 0,
    },
    {
        "runId": 486,
        "runName": "2025-1",
        "startTime": "2024-05-06T08:00:00-05:00",
        "endTime": "2024-10-01T00:00:00-05:00",
        "version": 0,
    },
    {
        "runId": 506,
        "runName": "2025-3",
        "startTime": "2025-09-05T15:06:00-05:00",
        "endTime": "2026-01-16T15:07:00-06:00",
        "version": 0,
    },
]


proposal_data = {
    "title": "Elucidation of DNA structure",
    "id": 158394,  # only 6 digits to test zero-fill
    "experimenters": [
        {
            "id": 1,
            "badge": "456789",
            "piFlag": "Y",
            "firstName": "Rosalind",
            "lastName": "Franklin",
            "institution": "Washington State University",
        },
        {
            "id": 2,
            "badge": "314769",
            "piFlag": "N",
            "firstName": "Francis",
            "lastName": "Crick",
            "institution": "Argonne National Laboratory",
        },
    ],
    "activities": [
        {
            "startTime": "2025-04-22T08:00:00-05:00",
            "endTime": "2025-04-24T08:00:00-05:00",
            "duration": 172800,
        }
    ],
    "totalShiftsRequested": "",
    "submittedDate": "",
    "proprietaryFlag": "",
    "mailInFlag": "",
    "startTime": "2025-04-22T08:00:00-05:00",
    "endTime": "2025-04-24T08:00:00-05:00",
    "duration": 172800,
}


esaf_data = {
    "esafId": 279007,
    "description": "DNA will be put in the X-ray machine and scienced.",
    "sector": "25",
    "esafTitle": "EXAFS of DNA structure",
    "experimentStartDate": "2025-04-15 08:00:00",
    "experimentEndDate": "2025-04-19 08:00:00",
    "esafStatus": "Approved",
    "experimentUsers": [
        {
            "badge": "123456",
            "badgeNumber": "123456",
            "firstName": "Rosalind",
            "lastName": "Franklin",
            "email": "rfranklin@anl.gov",
            "piFlag": "Yes",
        },
        {
            "badge": "123457",
            "badgeNumber": "123457",
            "firstName": "Francis",
            "lastName": "Crick",
            "email": "frick@anl.gov",
            "piFlag": "No",
        },
    ],
}


base_uri = "http://localhost:12345"


@pytest.fixture()
def api():
    stamina.set_testing(True)
    return bss.BssApi(username="", password="", station_name="25IDC", uri=base_uri)


async def test_get_esafs(httpx_mock, api):
    url = httpx.URL(
        f"{base_uri}/dm/esaf/stationEsafs/b'TWpWSlJFTT0='/b'TWpVdFNVUXRRdz09'",
        params={"year": "2025"},
    )
    httpx_mock.add_response(url=url, json=[esaf_data])
    esafs_ = await api.esafs(beamline="25-ID-C", year="2025")
    assert len(esafs_) == 1
    (this_esaf,) = esafs_
    assert this_esaf.title == esaf_data["esafTitle"]
    assert this_esaf.esaf_id == str(esaf_data["esafId"])
    assert len(this_esaf.users) == 2
    # Check properties of a signle user
    user = this_esaf.users[0]
    assert user.badge == "123456"
    assert user.first_name == "Rosalind"
    assert user.last_name == "Franklin"
    assert user.email == "rfranklin@anl.gov"
    assert user.is_pi == True


async def test_get_esaf(httpx_mock, api):
    httpx_mock.add_response(
        url=f"{base_uri}/dm/esaf/stationEsafsById/b'TWpWSlJFTT0='/279007",
        json=esaf_data,
    )
    esaf = await api.esaf(esaf_id="279007")


async def test_get_proposals(httpx_mock, api):
    url = httpx.URL(
        f"{base_uri}/dm/bss/stationProposals/b'TWpWSlJFTT0='/b'TWpVdFNVUXRRdz09'",
        params={"runName": "2025-1"},
    )
    httpx_mock.add_response(url=url, json=[proposal_data])
    proposals_ = await api.proposals(cycle="2025-1", beamline="25-ID-C")
    assert len(proposals_) == 1
    proposal = proposals_[0]
    assert proposal.proposal_id == "0158394"
    assert proposal.title == proposal_data["title"]
    # Check user list
    users = proposal.users
    assert len(users) == 2


async def test_get_proposal(httpx_mock, api):
    url = httpx.URL(
        f"{base_uri}/dm/bss/stationProposalsById/b'TWpWSlJFTT0='/0158394",
        params={"runName": "2025-1"},
    )
    httpx_mock.add_response(url=url, json=proposal_data)
    proposal = await api.proposal(proposal_id="0158394", cycle="2025-1")
    assert proposal.title == proposal_data["title"]


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
