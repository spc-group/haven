import pytest
from bluesky_queueserver_api import BPlan

from .qserver import QserverInfo


@pytest.mark.slow
def test_open_environment(qserver):
    status = qserver.api.status()
    assert status["worker_environment_exists"]


@pytest.mark.slow
def test_mv_plan(qserver: QserverInfo):
    item = BPlan("mv", "sim_async_motor", 5)
    if qserver.api is None:
        raise TypeError("Qserver API not available")
    result = qserver.api.item_add(item)
    assert result["success"]
    qserver.run_queue()
    # Check that the mv plan worked
    (history_item,) = qserver.api.history_get()["items"]
    assert history_item["result"]["exit_status"] == "completed"


@pytest.mark.slow
def test_xafs_scan_plan(qserver: QserverInfo):
    item = BPlan("xafs_scan", [], ["E", -10, 30, 5], E0=8333)
    if qserver.api is None:
        raise TypeError("Qserver API not available")
    result = qserver.api.item_add(item)
    assert result["success"]
    qserver.run_queue()
    # Check that the mv plan worked
    (history_item,) = qserver.api.history_get()["items"]
    assert history_item["result"]["exit_status"] == "completed"


@pytest.mark.slow
def test_plans_available(qserver: QserverInfo):
    if qserver.api is None:
        raise TypeError("Qserver API not available")
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
    plans_allowed = set(qserver.api.plans_allowed()["plans_allowed"].keys())
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
