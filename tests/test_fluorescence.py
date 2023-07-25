import asyncio
import pytest
from epics import caget

from unittest.mock import MagicMock
from ophyd import Kind, DynamicDeviceComponent as DDC
from bluesky import plans as bp

from haven.instrument import fluorescence_detector


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


# class Vortex(DxpDetectorBase):
#     mcas = DDC(
#         fluorescence_detector.add_mcas(range_=mca_range),
#         kind=active_kind,
#         default_read_attrs=[f"mca{i}" for i in mca_range],
#         default_configuration_attrs=[f"mca{i}" for i in mca_range],
#     )


# @pytest.fixture()
# def vortex(sim_registry, mocker):
#     mocker.patch("ophyd.signal.EpicsSignalBase._ensure_connected")
#     from haven.instrument.fluorescence_detector import make_dxp_device

#     # load_fluorescence_detectors(config=None)
#     vortex = asyncio.run(
#         make_dxp_device(
#             device_name="vortex_me4",
#             prefix="255idDXP",
#             num_elements=4,
#         )
#     )
#     # See if the device was loaded
#     return vortex


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
