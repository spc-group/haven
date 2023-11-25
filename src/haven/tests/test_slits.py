from unittest import mock

from haven.instrument import slits


def test_slits_tweak():
    """Test the PVs for the tweak forward/reverse."""
    slits_obj = slits.Optics2Slit2D_HV("255idc:KB_slits", name="KB_slits")
    # Check the inherited setpoint/readback PVs
    assert slits_obj.v.center.setpoint.pvname == "255idc:KB_slitsVcenter"
    assert slits_obj.v.center.readback.pvname == "255idc:KB_slitsVt2.D"
    # Check the tweak PVs
    assert slits_obj.v.center.tweak_value.pvname == "255idc:KB_slitsVcenter_tweakVal.VAL"
    assert slits_obj.v.center.tweak_reverse.pvname == "255idc:KB_slitsVcenter_tweak.A"
    assert slits_obj.v.center.tweak_forward.pvname == "255idc:KB_slitsVcenter_tweak.B"


def test_load_slits(sim_registry, monkeypatch):
    monkeypatch.setattr(slits, "await_for_connection", mock.AsyncMock())
    slits.load_slits()
    # Check that the slits were loaded
    device = sim_registry.find(label="slits")
    assert device.prefix == "vme_crate_ioc:KB"
