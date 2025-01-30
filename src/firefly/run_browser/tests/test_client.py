import pytest

from firefly.run_browser.client import DatabaseWorker


@pytest.fixture()
async def worker(tiled_client):
    worker = DatabaseWorker(tiled_client)
    await worker.change_catalog("255id_testing")
    return worker


@pytest.mark.asyncio
async def test_data_keys(worker):
    uids = (await worker.catalog.client).keys()
    await worker.load_selected_runs(uids)
    data_keys = await worker.data_keys("primary")
    assert "I0-mcs-scaler-channels-0-net_count" in data_keys
    assert "seq_num" in data_keys


@pytest.mark.asyncio
async def test_data_frames(worker):
    uids = (await worker.catalog.client).keys()
    await worker.load_selected_runs(uids)
    data_keys = await worker.data_frames("primary")
    # Check the results
    assert uids[0] in data_keys.keys()


@pytest.mark.asyncio
async def test_hints(worker):
    uids = (await worker.catalog.client).keys()
    await worker.load_selected_runs(uids)
    ihints, dhints = await worker.hints("primary")


@pytest.mark.asyncio
async def test_catalog_names(worker):
    assert (await worker.catalog_names()) == ["255id_testing", "255bm_testing"]


@pytest.mark.asyncio
async def test_filter_runs(worker):
    runs = await worker.load_all_runs(filters={"plan": "xafs_scan"})
    # Check that the runs were filtered
    assert len(runs) == 1


@pytest.mark.asyncio
async def test_distinct_fields(worker):
    distinct_fields = await worker.load_distinct_fields()
    # Check that the dictionary has the right structure
    for key in ["sample_name"]:
        assert key in distinct_fields.keys()


async def test_stream_names(worker):
    uids = (await worker.catalog.client).keys()
    await worker.load_selected_runs(uids)
    stream_names = await worker.stream_names()
    assert stream_names == ["primary"]


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
