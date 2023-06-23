from unittest.mock import MagicMock
from ophyd import Kind
from bluesky import plans as bp

import pytest

from epics import caget


def test_load_dxp(sim_registry, mocker):
    mocker.patch("ophyd.signal.EpicsSignalBase._ensure_connected")
    from haven.instrument.fluorescence_detector import load_fluorescence_detectors

    load_fluorescence_detectors(config=None)
    # See if the device was loaded
    vortex = sim_registry.find(name="vortex_me4")
    # Check that the MCA's are available
    assert hasattr(vortex.mcas, "mca1")
    assert hasattr(vortex.mcas, "mca2")
    assert hasattr(vortex.mcas, "mca3")
    assert hasattr(vortex.mcas, "mca4")
    # Check that MCA's have ROI's available
    assert hasattr(vortex.mcas.mca1, "rois")
    assert hasattr(vortex.mcas.mca1.rois, "roi1")
    # Check that bluesky hints were added
    assert hasattr(vortex.mcas.mca1.rois.roi1, "is_hinted")
    assert vortex.mcas.mca1.rois.roi1.is_hinted.pvname == "vortex_me4:mca1_R1BH"


@pytest.fixture()
def vortex(sim_registry, mocker):
    mocker.patch("ophyd.signal.EpicsSignalBase._ensure_connected")
    from haven.instrument.fluorescence_detector import load_fluorescence_detectors

    load_fluorescence_detectors(config=None)
    # See if the device was loaded
    vortex = sim_registry.find(name="vortex_me4")
    yield vortex


@pytest.mark.xfail
def test_enable_rois(vortex):
    assert hasattr(vortex.mcas.mca1, "rois")
    # Test that all channels are disabled by default
    assert "vortex_me4_mca1_rois_roi1" not in vortex.read_attrs
    assert "preset_live_time" in vortex.read_attrs
    assert "preset_mode" in vortex.configuration_attrs
    # Make sure config attrs are in the right place
    config_signals = [
        "mcas.mca3.rois.roi0.label",
        "mcas.mca3.rois.roi0.bkgnd_chans",
        "mcas.mca3.rois.roi0.hi_chan",
        "mcas.mca3.rois.roi0.lo_chan",
    ]
    normal_signals = ["mcas.mca3.rois.roi0.count", "mcas.mca3.rois.roi0.net_count"]
    omitted_signals = [
        "mcas.mca3.rois.roi0.preset_count",
        "mcas.mca3.rois.roi0.is_preset",
    ]
    for attr in config_signals:
        assert attr not in vortex.configuration_attrs
        assert attr not in vortex.read_attrs
    for attr in normal_signals:
        assert attr not in vortex.read_attrs
        assert attr not in vortex.configuration_attrs
    for attr in omitted_signals:
        assert attr not in vortex.read_attrs
        assert attr not in vortex.configuration_attrs
    # Enable all ROIs
    vortex.enable_rois()
    for attr in config_signals:
        assert attr in vortex.configuration_attrs
        assert attr not in vortex.read_attrs
    for attr in normal_signals:
        assert attr in vortex.read_attrs
        assert attr not in vortex.configuration_attrs
    for attr in omitted_signals:
        assert attr not in vortex.read_attrs
        assert attr not in vortex.configuration_attrs
    # Disable all ROIs
    vortex.disable_rois()
    for attr in config_signals:
        assert attr not in vortex.configuration_attrs
        assert attr not in vortex.read_attrs
    for attr in normal_signals:
        assert attr not in vortex.read_attrs
        assert attr not in vortex.configuration_attrs
    for attr in omitted_signals:
        assert attr not in vortex.read_attrs
        assert attr not in vortex.configuration_attrs


def test_enable_some_rois(vortex):
    vortex.disable_rois()
    assert "mcas.mca1.rois.roi0" not in vortex.read_attrs
    assert "mcas.mca1.rois.roi1" not in vortex.read_attrs
    # Enable just ROI0
    vortex.enable_rois(rois=[0])
    assert "mcas.mca1.rois.roi0" in vortex.read_attrs
    assert "mcas.mca1.rois.roi1" not in vortex.read_attrs
    # Disable just ROI0
    vortex.enable_rois()
    vortex.disable_rois(rois=[0])
    assert "mcas.mca1.rois.roi0" not in vortex.read_attrs
    assert "mcas.mca1.rois.roi1" in vortex.read_attrs


def test_enable_all_elements(vortex):
    vortex.enable_rois()
    vortex.disable_elements()
    assert "mcas.mca1.rois.roi0" not in vortex.read_attrs
    assert "mcas.mca1.rois.roi1" not in vortex.read_attrs
    # Enable just ROI0
    vortex.enable_elements(elements=[1])
    assert "mcas.mca1.rois.roi0" in vortex.read_attrs
    assert "mcas.mca2.rois.roi0" not in vortex.read_attrs
    # Disable just ROI0
    vortex.enable_elements()
    vortex.disable_elements(elements=[0])
    assert "mcas.mca0.rois.roi0" not in vortex.read_attrs
    assert "mcas.mca1.rois.roi0" in vortex.read_attrs


@pytest.mark.xfail
def test_with_plan(vortex):
    assert False, "Write test"


def test_stage_signal_names(sim_vortex):
    """Check that we can set the name of the detector ROIs dynamically."""
    dev = sim_vortex.mcas.mca1.rois.roi1
    dev.label.put("Ni-Ka")
    # Ensure the name isn't changed yet
    assert "Ni-Ka" not in dev.name
    assert "Ni_Ka" not in dev.name
    orig_name = dev.name
    dev.stage()
    try:
        result = dev.read()
    except Exception:
        raise
    else:
        assert "Ni-Ka" not in dev.name  # Make sure it gets sanitized
        assert "Ni_Ka" in dev.name
    finally:
        dev.unstage()
    # Name gets reset when unstaged
    assert dev.name == orig_name
    # Check acquired data uses dynamic names
    for res in result.keys():
        assert "Ni_Ka" in res


def test_stage_signal_hinted(sim_vortex):
    dev = sim_vortex.mcas.mca1.rois.roi1
    # Check that ROI is not hinted by default
    assert dev.name not in sim_vortex.hints
    # Enable the ROI by setting it's kind PV to "hinted"
    dev.is_hinted.put(True)
    # Ensure signals are not hinted before being staged
    assert dev.net_count.name not in sim_vortex.hints["fields"]
    try:
        dev.stage()
    except Exception:
        raise
    else:
        assert dev.net_count.name in sim_vortex.hints["fields"]
        assert (
            sim_vortex.mcas.mca1.rois.roi0.net_count.name
            not in sim_vortex.hints["fields"]
        )
    finally:
        dev.unstage()
    # Did it restore kinds properly when unstaging
    assert dev.net_count.name not in sim_vortex.hints["fields"]
    assert (
        sim_vortex.mcas.mca1.rois.roi0.net_count.name not in sim_vortex.hints["fields"]
    )
