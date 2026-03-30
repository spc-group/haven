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
