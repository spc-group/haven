from unittest import mock

from haven.instrument import slits


def test_load_slits(sim_registry, monkeypatch):
    monkeypatch.setattr(slits, "await_for_connection", mock.AsyncMock())
    slits.load_slits()
    # Check that the slits were loaded
    device = sim_registry.find(label="slits")
    assert device.prefix == "vme_crate_ioc:KB"
    assert device.h.center.setpoint.pvname == "vme_crate_ioc:KBHcenter"
