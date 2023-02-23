from haven.instrument.slits import load_slits

def test_load_slits(sim_registry):
    load_slits()
    # Check that the slits were loaded
    device = sim_registry.find(label="slits")
    assert device.prefix == "vme_crate_ioc:KB"
    assert device.h.center.setpoint.pvname == "vme_crate_ioc:KBHcenter"
