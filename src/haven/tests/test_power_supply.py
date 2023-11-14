from unittest import mock

from haven.instrument import power_supply


def test_load_power_supplies(sim_registry, monkeypatch):
    monkeypatch.setattr(power_supply, "await_for_connection", mock.AsyncMock())
    power_supply.load_power_supplies()
    # Test that the device has the right configuration
    devices = list(sim_registry.findall(label="power_supplies"))
    assert len(devices) == 2  # 2 channels on the device
    device = devices[0]
    assert "NHQ01_ch" in device.name
    pv_names = [d.potential.pvname for d in devices]
    assert "ps_ioc:NHQ01:Volt2_rbv" in pv_names
