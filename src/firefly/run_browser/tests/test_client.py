import re

import httpx
import pandas as pd
import pytest

from firefly.run_browser.client import DatabaseWorker

run_metadata_urls = re.compile(
    r"^http://localhost:8000/api/v1/metadata/([a-z]+)%2F([-a-z0-9]+)$"
)
stream_metadata_urls = re.compile(
    r"^http://localhost:8000/api/v1/metadata/"
    r"([a-z]+)%2F"  # catalog name
    r"([-a-z0-9]+)%2F"  # scan name
    r"streams%2F([a-z]+)$"  # stream name
)


@pytest.fixture()
def run_metadata_api(httpx_mock):
    def respond_with_metadata(request: httpx.Request):
        url = str(request.url)
        catalog, uid = run_metadata_urls.match(url).groups()
        md = {
            "data": {
                "attributes": {
                    "metadata": {
                        "start": {
                            "uid": uid,
                        }
                    }
                }
            }
        }
        return httpx.Response(
            status_code=200,
            json=md,
        )

    httpx_mock.add_callback(
        callback=respond_with_metadata,
        url=run_metadata_urls,
        is_reusable=True,
    )


@pytest.fixture()
async def worker(tiled_client):
    worker = DatabaseWorker()
    worker.catalog = tiled_client
    return worker


def md_to_json(metadata):
    response = {"data": {"attributes": {"metadata": metadata}}}
    return response


@pytest.mark.asyncio
async def test_data_keys(worker):
    uids = [
        "85573831-f4b4-4f64-b613-a6007bf03a8d",
        "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f",
    ]
    data_keys = await worker.data_keys(uids, "primary")
    assert "I0-mcs-scaler-channels-0-net_count" in data_keys
    assert "It-mcs-scaler-channels-3-net_count" in data_keys
    assert "seq_num" in data_keys


@pytest.mark.asyncio
async def test_metadata(worker):
    uids = [
        "85573831-f4b4-4f64-b613-a6007bf03a8d",
        "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f",
    ]
    md = await worker.metadata(uids)
    assert list(md.keys()) == uids
    assert md[uids[0]]["start"]["uid"] == uids[0]


@pytest.mark.asyncio
async def test_data_frames(worker, tiled_client):
    uids = [
        "85573831-f4b4-4f64-b613-a6007bf03a8d",
        "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f",
    ]
    data_frames = await worker.data_frames(uids, "primary")
    # Check the results
    assert isinstance(data_frames["85573831-f4b4-4f64-b613-a6007bf03a8d"], pd.DataFrame)


@pytest.mark.asyncio
async def test_hints(worker):
    # httpx_mock.add_response(
    #     url=run_metadata_urls,
    #     json=md_to_json(
    #         {
    #             "start": {
    #                 "hints": {
    #                     "dimensions": [
    #                         [["aerotech_vert"], "primary"],
    #                         [["aerotech_horiz"], "primary"],
    #                     ],
    #                 }
    #             }
    #         }
    #     ),
    # )
    # # Respond with stream hints
    # httpx_mock.add_response(
    #     url=stream_metadata_urls,
    #     json=md_to_json(
    #         {
    #             "hints": {
    #                 "Ipreslit": {"fields": ["Ipreslit_net_counts"]},
    #                 "CdnIPreKb": {"fields": ["CdnIPreKb_net_counts"]},
    #                 "I0": {"fields": ["I0_net_counts"]},
    #                 "CdnIt": {"fields": ["CdnIt_net_counts"]},
    #                 "aerotech_vert": {"fields": ["aerotech_vert"]},
    #                 "aerotech_horiz": {"fields": ["aerotech_horiz"]},
    #                 "Ipre_KB": {"fields": ["Ipre_KB_net_counts"]},
    #                 "CdnI0": {"fields": ["CdnI0_net_counts"]},
    #                 "It": {"fields": ["It_net_counts"]},
    #             },
    #         }
    #     ),
    # )
    uids = [
        "85573831-f4b4-4f64-b613-a6007bf03a8d",
        "7d1daf1d-60c7-4aa7-a668-d1cd97e5335f",
    ]
    ihints, dhints = await worker.hints(uids, "primary")
    assert ihints == {"aerotech_vert", "aerotech_horiz"}


@pytest.mark.asyncio
async def test_filter_runs(worker):
    runs = await worker.load_all_runs(filters={"plan": "xafs_scan"})
    # Check that the runs were filtered
    assert len(runs) == 1


@pytest.mark.asyncio
async def test_distinct_fields(worker):
    distinct_fields = [field async for field in worker.distinct_fields()]
    keys, fields = zip(*distinct_fields)
    # Check that the dictionary has the right structure
    for key in ["start.plan_name"]:
        assert key in keys


async def test_stream_names(worker):
    stream_names = await worker.stream_names(["85573831-f4b4-4f64-b613-a6007bf03a8d"])
    assert sorted(stream_names) == ["baseline", "primary"]


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
