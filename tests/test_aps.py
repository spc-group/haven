import pytest

from haven.instrument.aps import load_aps, ApsMachine


def test_load_aps(sim_registry):
    load_aps()
    aps = sim_registry.find(name="APS")
    assert hasattr(aps, "current")


def test_read_attrs():
    device = ApsMachine(name="Aps")
    read_attrs = ["current", "lifetime"]
    for attr in read_attrs:
        assert attr in device.read_attrs


def test_config_attrs():
    device = ApsMachine(name="Aps")
    config_attrs = [
        "aps_cycle",
        "machine_status",
        "operating_mode",
        "shutter_permit",
        "fill_number",
        "orbit_correction",
        "global_feedback",
        "global_feedback_h",
        "global_feedback_v",
        "operator_messages",
    ]
    for attr in config_attrs:
        assert attr in device.configuration_attrs


def test_load_apsbss(sim_registry):
    load_aps()
    bss = sim_registry.find(name="bss")
    assert hasattr(bss, "esaf")
    assert hasattr(bss.esaf, 'esaf_id')
    assert bss.esaf.esaf_id.pvname == "100id:bss:esaf:id"
