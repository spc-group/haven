from unittest import mock

from haven.instrument.xray_source import load_xray_sources
import haven


def test_load_xray_sources(sim_registry, ioc_undulator, monkeypatch):
    monkeypatch.setattr(
        haven.instrument.xray_source, "await_for_connection", mock.AsyncMock()
    )
    load_xray_sources()
    # Check that the undulator was added to the registry
    dev = sim_registry.find(label="xray_sources")
    assert dev.prefix == "ID255:"
    assert dev.gap.pvname == "ID255:Gap"
