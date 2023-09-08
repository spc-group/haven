"""Tests for all the fluorescence detectors.

These tests are mostly parameterized to ensure that both DXP and
Xspress detectors share a common interface. A few of the tests are
specific to one device or another.

"""

import logging
from pathlib import Path
import asyncio
from unittest.mock import MagicMock
import time

import numpy as np
import pytest
from epics import caget
from ophyd import Kind, DynamicDeviceComponent as DDC, OphydObject
from bluesky import plans as bp

from haven.instrument.dxp import parse_xmap_buffer, load_dxp
from haven.instrument.xspress import load_xspress


DETECTORS = ['dxp', 'xspress']
# DETECTORS = ['dxp']


@pytest.fixture()
def vortex(request):
    """Parameterized fixture for creating a Vortex device with difference
    electronics support.

    """
    # Figure out which detector we're using
    det = request.getfixturevalue(request.param)
    yield det


def test_load_xspress(sim_registry, mocker):
    load_xspress(config=None)
    vortex = sim_registry.find(name="vortex_me5")
    assert vortex.mcas.component_names == ("mca0", "mca1", "mca2", "mca3", "mca4")


def test_load_dxp(sim_registry):
    load_dxp(config=None)
    # See if the device was loaded
    vortex = sim_registry.find(name="vortex_me4")
    # Check that the MCA's are available
    assert hasattr(vortex.mcas, "mca0")
    assert hasattr(vortex.mcas, "mca1")
    assert hasattr(vortex.mcas, "mca2")
    assert hasattr(vortex.mcas, "mca3")
    # Check that MCA's have ROI's available
    assert hasattr(vortex.mcas.mca1, "rois")
    assert hasattr(vortex.mcas.mca1.rois, "roi0")
    # Check that bluesky hints were added
    assert hasattr(vortex.mcas.mca1.rois.roi0, "use")
    # assert vortex.mcas.mca1.rois.roi1.is_hinted.pvname == "vortex_me4:mca1_R1BH"


@pytest.mark.parametrize('vortex', DETECTORS, indirect=True)
def test_roi_size(vortex, caplog):
    """Do the signals for max/size auto-update."""
    from pprint import pprint
    roi = vortex.mcas.mca0.rois.roi0
    # Check that we can set the lo_chan without error in the callback
    with caplog.at_level(logging.ERROR):
        roi.lo_chan.set(10).wait()
    for record in caplog.records:
        assert "Another set() call is still in progress" not in record.exc_text, record.exc_text
    # Update the size and check the maximum
    roi.size.set(7).wait()
    assert roi.hi_chan.get() == 17
    # Update the maximum and check the size
    roi.hi_chan.set(28).wait()
    assert roi.size.get() == 18
    # Update the minimum and check the size
    roi.lo_chan.set(25).wait()
    assert roi.size.get() == 3


@pytest.mark.parametrize('vortex', DETECTORS, indirect=True)        
def test_enable_some_rois(vortex):
    """Test that the correct ROIs are enabled/disabled."""
    print(vortex)
    statuses = vortex.enable_rois(rois=[2, 5], elements=[1, 3])
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait()
        # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.use.get(use_monitor=False)
    assert hinted == 1


@pytest.mark.parametrize('vortex', DETECTORS, indirect=True)    
def test_enable_rois(vortex):
    """Test that the correct ROIs are enabled/disabled."""
    statuses = vortex.enable_rois()
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait()
        # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.use.get(use_monitor=False)
    assert hinted == 1


@pytest.mark.parametrize('vortex', DETECTORS, indirect=True)
def test_disable_some_rois(vortex):
    """Test that the correct ROIs are enabled/disabled."""
    statuses = vortex.enable_rois(rois=[2, 5], elements=[1, 3])
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait()
    # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.use.get(use_monitor=False)
    assert hinted == 1
    statuses = vortex.disable_rois(rois=[2, 5], elements=[1, 3])
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait()
    # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.use.get(use_monitor=False)
    assert hinted == 0


@pytest.mark.parametrize('vortex', DETECTORS, indirect=True)
def test_disable_rois(vortex):
    """Test that the correct ROIs are enabled/disabled."""
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
    hinted = roi.use.get(use_monitor=False)
    assert hinted == 0


@pytest.mark.xfail
def test_with_plan(vortex):
    assert False, "Write test"


@pytest.mark.parametrize('vortex', DETECTORS, indirect=True)
def test_stage_signal_names(vortex):
    """Check that we can set the name of the detector ROIs dynamically."""
    dev = vortex.mcas.mca1.rois.roi1
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


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_read_and_config_attrs(vortex):
    vortex.mcas.mca0.read_attrs
    expected_read_attrs = [
        "mcas",
    ]
    if hasattr(vortex, 'cam'):
        expected_read_attrs.append("cam")
    # Add attrs for each MCA and ROI.
    for mca in range(vortex.num_elements):
        expected_read_attrs.extend([
            f"mcas.mca{mca}",
            f"mcas.mca{mca}.rois",
            f"mcas.mca{mca}.spectrum",
            f"mcas.mca{mca}.total_count",
            # f"mcas.mca{mca}.input_count_rate",
            # f"mcas.mca{mca}.output_count_rate",
            f"mcas.mca{mca}.dead_time",
            # f"mcas.mca{mca}.background",
        ])
        for roi in range(vortex.num_rois):
            expected_read_attrs.extend([
                f"mcas.mca{mca}.rois.roi{roi}",
                f"mcas.mca{mca}.rois.roi{roi}.count",
                f"mcas.mca{mca}.rois.roi{roi}.net_count",
            ])
    assert sorted(vortex.read_attrs) == sorted(expected_read_attrs)


@pytest.mark.parametrize('vortex', DETECTORS, indirect=True)
def test_stage_signal_hinted(vortex):
    dev = vortex.mcas.mca0.rois.roi1
    # Check that ROI is not hinted by default
    assert dev.name not in vortex.hints
    # Enable the ROI by setting it's kind PV to "hinted"
    dev.use.set(True).wait()
    # Ensure signals are not hinted before being staged
    assert dev.net_count.name not in vortex.hints["fields"]
    try:
        dev.stage()
    except Exception:
        raise
    else:
        assert dev.net_count.name in vortex.hints["fields"]
        assert (
            vortex.mcas.mca1.rois.roi0.net_count.name
            not in vortex.hints["fields"]
        )
    finally:
        dev.unstage()
    # Did it restore kinds properly when unstaging
    assert dev.net_count.name not in vortex.hints["fields"]
    assert (
        vortex.mcas.mca1.rois.roi0.net_count.name not in vortex.hints["fields"]
    )


@pytest.mark.parametrize('vortex', DETECTORS, indirect=True)
@pytest.mark.xfail
def test_dxp_kickoff(vortex):
    vortex = vortex
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


def test_dxp_acquire(dxp):
    """Check that the DXP acquire mimics that of the area detector base."""
    assert dxp.stop_all.get(use_monitor=False) == 0
    assert dxp.erase_start.get(use_monitor=False) == 0
    dxp.acquire.set(1).wait()
    assert dxp.stop_all.get(use_monitor=False) == 0
    assert dxp.erase_start.get(use_monitor=False) == 1
    dxp.acquire.set(0).wait()
    assert dxp.stop_all.get(use_monitor=False) == 1
    assert dxp.erase_start.get(use_monitor=False) == 1

    # Now test the reverse behavior
    dxp.acquire.set(0).wait()
    assert dxp.acquire.get(use_monitor=False) == 0
    dxp.acquiring.set(1).wait()
    assert dxp.acquire.get(use_monitor=False) == 1
    dxp.acquiring.set(0).wait()
    assert dxp.acquire.get(use_monitor=False) == 0


def test_complete_dxp(dxp):
    """Check the behavior of the DXP electornic's fly-scan complete call."""
    vortex = dxp
    vortex.write_path = "M:\\tmp\\"
    vortex.read_path = "/net/s20data/sector20/tmp/"
    vortex.acquire._readback = 1
    status = vortex.complete()
    time.sleep(0.01)
    assert vortex.stop_all.get(use_monitor=False) == 1
    assert not status.done
    vortex.acquiring.set(0)
    status.wait()
    assert status.done


def test_complete_xspress(xspress):
    """Check the behavior of the Xspress3 electornic's fly-scan complete call."""
    vortex = xspress
    vortex.acquire.sim_put(1)
    status = vortex.complete()
    time.sleep(0.01)
    assert vortex.acquire.get(use_monitor=False) == 0
    assert status.done


@pytest.mark.parametrize('vortex', DETECTORS, indirect=True)
@pytest.mark.xfail
def test_parse_xmap_buffer(vortex):
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


@pytest.mark.parametrize('vortex', DETECTORS, indirect=True)
def test_roi_calcs(vortex):
    # Check that the ROI calc signals exist
    assert isinstance(vortex.roi_sums.roi0, OphydObject)
    # Set some fake ROI values
    print(vortex.mcas.mca0.rois.roi0.net_count)
    vortex.mcas.mca0.rois.roi0.net_count.sim_put(5)
    assert vortex.roi_sums.roi0.get() == 5


@pytest.mark.parametrize('vortex', DETECTORS, indirect=True)
def test_mca_calcs(vortex):
    # Check that the ROI calc signals exist
    assert isinstance(vortex.mcas.mca0.total_count, OphydObject)
    # Does it sum together the total counts?
    spectrum = np.random.randint(2**16, size=(vortex.num_rois))
    mca = vortex.mcas.mca0
    mca.spectrum.sim_put(spectrum)
    assert mca.total_count.get(use_monitor=False) == np.sum(spectrum)

