import pytest

from haven.instrument.aps import load_aps


def test_load_aps(sim_registry):
    load_aps()
    aps = sim_registry.find(name="APS")
    assert hasattr(aps, "current")
