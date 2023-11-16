from haven.instrument.xray_source import load_xray_sources


def test_load_xray_sources(sim_registry, beamline_connected):
    load_xray_sources()
    # Check that the undulator was added to the registry
    dev = sim_registry.find(label="xray_sources")
    assert dev.prefix == "ID255:"
    assert dev.gap.pvname == "ID255:Gap"
