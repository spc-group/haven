from pathlib import Path
import asyncio
from unittest.mock import MagicMock

import numpy as np
import pytest
from epics import caget
from ophyd import Kind, DynamicDeviceComponent as DDC
from bluesky import plans as bp

from haven.instrument.fluorescence_detector import parse_xmap_buffer


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


def test_enable_some_rois(sim_vortex):
    """Test that the correct ROIs are enabled/disabled."""
    vortex = sim_vortex
    statuses = vortex.enable_rois(rois=[2, 5], elements=[1, 3])
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait()
        # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.is_hinted.get(use_monitor=False)
    assert hinted == 1


def test_enable_rois(sim_vortex):
    """Test that the correct ROIs are enabled/disabled."""
    vortex = sim_vortex
    statuses = vortex.enable_rois()
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait()
        # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.is_hinted.get(use_monitor=False)
    assert hinted == 1


def test_disable_some_rois(sim_vortex):
    """Test that the correct ROIs are enabled/disabled."""
    vortex = sim_vortex
    statuses = vortex.enable_rois(rois=[2, 5], elements=[1, 3])
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait()
    # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.is_hinted.get(use_monitor=False)
    assert hinted == 1
    statuses = vortex.disable_rois(rois=[2, 5], elements=[1, 3])
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait()
    # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.is_hinted.get(use_monitor=False)
    assert hinted == 0


def test_disable_rois(sim_vortex):
    """Test that the correct ROIs are enabled/disabled."""
    vortex = sim_vortex
    statuses = vortex.enable_rois()
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait()

    statuses = vortex.disable_rois()
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait()
        # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.is_hinted.get(use_monitor=False)
    assert hinted == 0


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


@pytest.mark.xfail
def test_dxp_kickoff(sim_vortex):
    vortex = sim_vortex
    vortex.write_path = "M:\\tmp\\"
    vortex.read_path = "/net/s20data/sector20/tmp/"
    [
        s.wait()
        for s in [
            vortex.acquiring.set(0),
            vortex.collect_mode.set("MCA Spectrum"),
            vortex.erase_start.set(0),
            vortex.pixel_advance_mode.set("Sync"),
        ]
    ]
    # Ensure that the vortex is in its normal operating state
    assert vortex.collect_mode.get(use_monitor=False) == "MCA Spectrum"
    # Check that the kickoff status ended properly
    status = vortex.kickoff()
    assert not status.done
    vortex.acquiring.set(1)
    status.wait()
    assert status.done
    assert status.success
    # Check that the right signals were set during  kick off
    assert vortex.collect_mode.get(use_monitor=False) == "MCA Mapping"
    assert vortex.erase_start.get(use_monitor=False) == 1
    assert vortex.pixel_advance_mode.get(use_monitor=False) == "Gate"
    # Check that the netCDF writer was setup properly
    assert vortex.net_cdf.enable.get(use_monitor=False) == "Enable"
    assert vortex.net_cdf.file_path.get(use_monitor=False) == "M:\\tmp\\"
    assert vortex.net_cdf.file_name.get(use_monitor=False) == "fly_scan_temp.nc"
    assert vortex.net_cdf.capture.get(use_monitor=False) == 1


def test_dxp_complete(sim_vortex):
    vortex = sim_vortex
    vortex.write_path = "M:\\tmp\\"
    vortex.read_path = "/net/s20data/sector20/tmp/"
    [
        s.wait()
        for s in [
            vortex.acquiring.set(1),
            vortex.stop_all.set(0),
        ]
    ]
    status = vortex.complete()
    assert vortex.stop_all.get(use_monitor=False) == 1
    assert not status.done
    vortex.acquiring.set(0)
    status.wait()
    assert status.done


@pytest.mark.xfail
def test_parse_xmap_buffer(sim_vortex):
    """The output for fly-scanning with the DXP-based readout electronics
    is a raw uint16 buffer that must be parsed by the ophyd device
    according to section 5.3.3 of
    https://cars9.uchicago.edu/software/epics/XMAP_User_Manual.pdf

    """
    fp = Path(__file__)
    buff = np.loadtxt(fp.parent / "dxp_3px_4elem_Fe55.txt")
    data = parse_xmap_buffer(buff)
    assert isinstance(data, dict)
    assert data["num_pixels"] == 3
    assert len(data["pixels"]) == 3
