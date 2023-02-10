from unittest.mock import MagicMock
from ophyd import Kind
from bluesky import plans as bp

import pytest

from epics import caget


@pytest.fixture
def vortex():
    return XspressDetector("xspress:", name="vortex")


def test_staging(vortex, ioc_vortex):
    # Check starting conditions
    assert vortex.num_frames.get() == 1
    assert caget("xspress:NumImages") == 1
    assert caget("xspress:TriggerMode") == 1
    # Check that the number of frames gets set
    vortex.stage_num_frames = 48
    # Check the detector was set up correctly
    vortex.stage()
    assert caget("xspress:NumImages") == 48
    assert caget("xspress:TriggerMode") == 3
    # Did the values get reset when unstaged
    vortex.unstage()
    assert caget("xspress:NumImages") == 1
    assert caget("xspress:TriggerMode") == 1


def _ensure_connected(*args, **kwargs):
    pass


def test_load_dxp(sim_registry, mocker):
    mocker.patch('ophyd.signal.EpicsSignalBase._ensure_connected')
    from haven.instrument.fluorescence_detector import load_fluorescence_detectors
    load_fluorescence_detectors(config=None)
    # See if the device was loaded
    vortex = sim_registry.find(name="vortex_me4")
    # Patch some 
    # Check that the MCA's are available
    assert hasattr(vortex, "mca1")
    assert hasattr(vortex, "mca2")
    assert hasattr(vortex, "mca3")
    assert hasattr(vortex, "mca4")
    # Check that MCA's have ROI's available
    assert hasattr(vortex.mca1, "rois")
    assert hasattr(vortex.mca1.rois, "roi1")


@pytest.fixture()
def vortex(sim_registry, mocker):
    mocker.patch('ophyd.signal.EpicsSignalBase._ensure_connected')
    from haven.instrument.fluorescence_detector import load_fluorescence_detectors
    load_fluorescence_detectors(config=None)
    # See if the device was loaded
    vortex = sim_registry.find(name="vortex_me4")
    yield vortex


def test_enable_rois(vortex):
    assert hasattr(vortex.mca1, "rois")
    # Test that all channels are disabled by default
    assert "vortex_me4_mca1_rois_roi1" not in vortex.read_attrs
    assert "preset_live_time" in vortex.read_attrs
    assert "preset_mode" in vortex.configuration_attrs
    # Make sure config attrs are in the right place
    config_signals = [
        'mca3.rois.roi0.label',
        'mca3.rois.roi0.bkgnd_chans',
        'mca3.rois.roi0.hi_chan',
        'mca3.rois.roi0.lo_chan',
    ]
    normal_signals = ['mca3.rois.roi0.count', 'mca3.rois.roi0.net_count']
    omitted_signals = ['mca3.rois.roi0.preset_count',
                     'mca3.rois.roi0.is_preset']
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
    assert "mca1.rois.roi0" not in vortex.read_attrs
    assert "mca1.rois.roi1" not in vortex.read_attrs
    # Enable just ROI0
    vortex.enable_rois(rois=[0])
    assert "mca1.rois.roi0" in vortex.read_attrs
    assert "mca1.rois.roi1" not in vortex.read_attrs
    # Disable just ROI0
    vortex.enable_rois()
    vortex.disable_rois(rois=[0])
    assert "mca1.rois.roi0" not in vortex.read_attrs
    assert "mca1.rois.roi1" in vortex.read_attrs    
    

@pytest.mark.xfail
def test_with_plan(vortex):
    ...
