import time

import pytest
from bluesky_queueserver_api import BPlan
from bluesky_queueserver_api.zmq import REManagerAPI

from .qserver import QserverInfo

TICK = 0.5


def open_environment(api, timeout: int | float = 60) -> None:
    environment_is_open = None
    result = api.environment_open()
    assert result["success"]
    # Poll the qserver until the environment is successfully opened
    t0 = time.monotonic()
    while (time.monotonic() - t0) < timeout:
        if api.status()["worker_environment_exists"]:
            break
        time.sleep(TICK)
    else:
        raise TimeoutError(
            f"Qserver environment at did not open with {timeout} seconds."
        )


def run_queue(api):
    result = api.queue_start()
    assert result["success"]
    is_idle = False
    while not is_idle:
        is_idle = api.status()["manager_state"] == "idle"
        time.sleep(TICK)


@pytest.fixture()
def api(qserver: QserverInfo):
    api = REManagerAPI(
        zmq_control_addr=qserver.control_addr, zmq_info_addr=qserver.info_addr
    )
    open_environment(api)
    return api


@pytest.mark.slow
def test_open_environment(api):
    status = api.status()
    assert status["worker_environment_exists"]


@pytest.mark.slow
def test_mv_plan(api):
    item = BPlan("mv", "sim_async_motor", 5)
    result = api.item_add(item)
    assert result["success"]
    run_queue(api)
    # Check that the mv plan worked
    (history_item,) = api.history_get()["items"]
    assert history_item["result"]["exit_status"] == "completed"


@pytest.mark.slow
def test_xafs_scan_plan(api):
    item = BPlan("xafs_scan", [], ["E", -10, 30, 5], E0=8333)
    result = api.item_add(item)
    assert result["success"]
    run_queue(api)
    # Check that the mv plan worked
    (history_item,) = api.history_get()["items"]
    assert history_item["result"]["exit_status"] == "completed"


@pytest.mark.slow
def test_plans_available(api):
    expected_plans = {
        "abs_set",
        "rel_set",
        "adaptive_xanes",
        "emission_map_scan",
        "fly_scan",
        "grid_fly_scan",
        "grid_scan",
        "mv",
        "mvr",
        "record_dark_current",
        "rel_grid_scan",
        "rel_scan",
        "scan",
        "set_energy",
        "sleep",
        "xafs_scan",
        "auto_gain",
        "calibrate",
        "count",
    }
    plans_allowed = set(api.plans_allowed()["plans_allowed"].keys())
    assert plans_allowed == expected_plans


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2026, UChicago Argonne, LLC
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
