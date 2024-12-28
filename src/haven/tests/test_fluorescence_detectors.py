"""Tests for the old-style fluorescence detectors.

.. note::

  These tests are deprecated because of the move to Ophyd-async
  devices. The tests have been moved to either ``test_xspress.py`` or
  the upcoming ``test_dxp.py``.

These tests are mostly parameterized to ensure that both DXP and
Xspress detectors share a common interface. A few of the tests are
specific to one device or another.

"""

import logging
import time
from pathlib import Path

import numpy as np
import pytest
from ophyd import OphydObject, Signal

from haven.devices.dxp import parse_xmap_buffer

# DETECTORS = ["dxp", "xspress"]
DETECTORS = ["dxp"]


@pytest.fixture()
def vortex(request):
    """Parameterized fixture for creating a Vortex device with difference
    electronics support.

    """
    # Figure out which detector we're using
    det = request.getfixturevalue(request.param)
    yield det


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_roi_size(vortex, caplog):
    """Do the signals for max/size auto-update."""
    roi = vortex.mcas.mca0.rois.roi0
    # Check that we can set the lo_chan without error in the callback
    with caplog.at_level(logging.ERROR):
        roi.lo_chan.set(10).wait(timeout=3)
    for record in caplog.records:
        assert (
            "Another set() call is still in progress" not in record.exc_text
        ), record.exc_text
    # Update the size and check the maximum
    roi.size.set(7).wait(timeout=3)
    assert roi.hi_chan.get() == 17
    # Update the maximum and check the size
    roi.hi_chan.set(28).wait(timeout=3)
    assert roi.size.get() == 18
    # Update the minimum and check the size
    roi.lo_chan.set(25).wait(timeout=3)
    assert roi.size.get() == 3


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_roi_size_concurrency(vortex, caplog):
    roi = vortex.mcas.mca0.rois.roi0
    # Set up the roi limits
    roi.lo_chan.set(12).wait(timeout=3)
    roi.size.set(13).wait(timeout=3)
    assert roi.hi_chan.get() == 25
    # Change two signals together
    statuses = [
        roi.lo_chan.set(3),
        roi.hi_chan.set(5),
    ]
    for st in statuses:
        st.wait(timeout=3)
    # Check that the signals were set correctly
    assert roi.lo_chan.get() == 3
    assert roi.hi_chan.get() == 5
    assert roi.size.get() == 2


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_enable_some_rois(vortex):
    """Test that the correct ROIs are enabled/disabled."""
    statuses = vortex.enable_rois(rois=[2, 5], elements=[1, 3])
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait(timeout=3)
        # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    is_used = roi.use.get(use_monitor=False)
    assert is_used == 1


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_enable_rois(vortex):
    """Test that the correct ROIs are enabled/disabled."""
    statuses = vortex.enable_rois()
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait(timeout=3)
        # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.use.get(use_monitor=False)
    assert hinted == 1


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_disable_some_rois(vortex):
    """Test that the correct ROIs are enabled/disabled."""
    statuses = vortex.enable_rois(rois=[2, 5], elements=[1, 3])
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait(timeout=3)
    # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.use.get(use_monitor=False)
    assert hinted == 1
    statuses = vortex.disable_rois(rois=[2, 5], elements=[1, 3])
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait(timeout=3)
    # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.use.get(use_monitor=False)
    assert hinted == 0


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_disable_rois(vortex):
    """Test that the correct ROIs are enabled/disabled."""
    statuses = vortex.enable_rois()
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait(timeout=3)

    statuses = vortex.disable_rois()
    # Give the IOC time to change the PVs
    for status in statuses:
        status.wait(timeout=3)
        # Check that at least one of the ROIs was changed
    roi = vortex.mcas.mca1.rois.roi2
    hinted = roi.use.get(use_monitor=False)
    assert hinted == 0


@pytest.mark.skip(reason="fails, and will be replaced by ophyd-async device soon")
@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_stage_signal_names(vortex):
    """Check that we can set the name of the detector ROIs dynamically."""
    dev = vortex.mcas.mca1.rois.roi1
    dev.label.put("~Ni-Ka", timeout=3)
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
        assert "~" not in dev.name  # Make sure it gets sanitized
        assert "__" not in dev.name  # Tildes sanitize bad but used for `use` signal
        assert "Ni_Ka" in dev.name
    finally:
        dev.unstage()
    # Name gets reset when unstaged
    assert dev.name == orig_name
    assert dev.count.name == f"{orig_name}_count"
    # Check acquired data uses dynamic names
    for res in result.keys():
        assert "Ni_Ka" in res


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_read_and_config_attrs(vortex):
    vortex.mcas.mca0.read_attrs
    expected_read_attrs = [
        "mcas",
        "roi_sums",
        "dead_time_average",
        "dead_time_min",
        "dead_time_max",
    ]
    if hasattr(vortex, "cam"):
        expected_read_attrs.append("cam")
    # Add attrs for summing ROIs across elements
    for roi in range(vortex.num_rois):
        expected_read_attrs.extend(
            [
                f"roi_sums.roi{roi}",
                f"roi_sums.roi{roi}.count",
                f"roi_sums.roi{roi}.net_count",
            ]
        )
    # Add attrs for each MCA and ROI.
    for mca in range(vortex.num_elements):
        expected_read_attrs.extend(
            [
                f"mcas.mca{mca}",
                f"mcas.mca{mca}.rois",
                f"mcas.mca{mca}.spectrum",
                f"mcas.mca{mca}.total_count",
                # f"mcas.mca{mca}.input_count_rate",
                # f"mcas.mca{mca}.output_count_rate",
                f"mcas.mca{mca}.dead_time_percent",
                f"mcas.mca{mca}.dead_time_factor",
                # f"mcas.mca{mca}.background",
            ]
        )
        if hasattr(vortex.mcas.mca0, "clock_ticks"):
            expected_read_attrs.append(f"mcas.mca{mca}.clock_ticks")
        for roi in range(vortex.num_rois):
            expected_read_attrs.extend(
                [
                    f"mcas.mca{mca}.rois.roi{roi}",
                    f"mcas.mca{mca}.rois.roi{roi}.count",
                    f"mcas.mca{mca}.rois.roi{roi}.net_count",
                ]
            )
    assert sorted(vortex.read_attrs) == sorted(expected_read_attrs)


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_use_signal(vortex):
    """Check that the ``.use`` ROI signal properly mangles the label.

    It uses label mangling instead of any underlying PVs because
    different detector types don't have this feature or use it in an
    undesirable way.

    """
    roi = vortex.mcas.mca0.rois.roi1
    roi.label.sim_put("Fe-55")
    # Enable the ROI and see if the name is updated
    roi.use.set(False).wait(timeout=3)
    assert roi.label.get() == "~Fe-55"
    # Disable the ROI and see if it goes back
    roi.use.set(True).wait(timeout=3)
    assert roi.label.get() == "Fe-55"
    # Set the label manually and see if the use signal changes
    roi.label.set("~Fe-55").wait(timeout=3)
    assert not bool(roi.use.get())


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_stage_hints(vortex):
    """Check that enabled ROIs get hinted."""
    roi0 = vortex.mcas.mca0.rois.roi0
    roi0.label.put("", timeout=3)
    roi0.use.put(1, timeout=3)
    roi1 = vortex.mcas.mca0.rois.roi1
    roi1.label.put("", timeout=3)
    roi1.use.put(0, timeout=3)
    # Ensure the hints aren't applied yet
    assert roi0.count.name not in vortex.hints["fields"]
    assert roi1.count.name not in vortex.hints["fields"]
    # Stage the detector ROIs
    try:
        roi0.stage()
        roi1.stage()
    except Exception:
        raise
    else:
        # Check that only the enabled ROI gets hinted
        assert roi0.count.name in vortex.hints["fields"]
        assert roi1.count.name not in vortex.hints["fields"]
    finally:
        roi0.unstage()
        roi1.unstage()
    # Name gets reset when unstaged
    assert roi0.count.name not in vortex.hints["fields"]
    assert roi1.count.name not in vortex.hints["fields"]


@pytest.mark.skip(reason="DXP fly-scanning not yet implemented")
def test_kickoff_dxp(dxp):
    vortex = dxp
    vortex.write_path = "M:\\tmp\\"
    vortex.read_path = "/net/s20data/sector20/tmp/"
    [
        s.wait(timeout=3)
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
    status.wait(timeout=3)
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
    dxp.acquire.set(1).wait(timeout=3)
    assert dxp.stop_all.get(use_monitor=False) == 0
    assert dxp.erase_start.get(use_monitor=False) == 1
    dxp.acquire.set(0).wait(timeout=3)
    assert dxp.stop_all.get(use_monitor=False) == 1
    assert dxp.erase_start.get(use_monitor=False) == 1

    # Now test the reverse behavior
    dxp.acquire.set(0).wait(timeout=3)
    assert dxp.acquire.get(use_monitor=False) == 0
    dxp.acquiring.set(1).wait(timeout=3)
    assert dxp.acquire.get(use_monitor=False) == 1
    dxp.acquiring.set(0).wait(timeout=3)
    assert dxp.acquire.get(use_monitor=False) == 0


@pytest.mark.skip(reason="DXP fly-scanning not yet implemented")
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
    status.wait(timeout=3)
    assert status.done


@pytest.mark.skip(reason="DXP fly-scanning not yet implemented")
def test_parse_dxp_buffer(dxp):
    """The output for fly-scanning with the DXP-based readout electronics
    is a raw uint16 buffer that must be parsed by the ophyd device
    according to section 5.3.3 of
    https://cars9.uchicago.edu/software/epics/XMAP_User_Manual.pdf

    """
    vortex = dxp
    fp = Path(__file__)
    buff = np.loadtxt(fp.parent / "dxp_3px_4elem_Fe55.txt")
    data = parse_xmap_buffer(buff)
    assert isinstance(data, dict)
    assert data["num_pixels"] == 3
    assert len(data["pixels"]) == 3


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_device_sums(vortex):
    """Does the device correctly calculate the overall counts, etc."""
    assert isinstance(vortex.total_count, Signal)
    spectrum = np.arange(256)
    vortex.mcas.mca0.spectrum.sim_put(spectrum)
    expected = spectrum.sum()
    assert vortex.total_count.get() == expected
    # Add a second spectrum
    spectrum_2 = np.arange(256, 512)
    vortex.mcas.mca1.spectrum.sim_put(spectrum_2)
    expected += spectrum_2.sum()
    assert vortex.total_count.get() == expected


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_roi_sums(vortex):
    """Check that we get the sum over all elements for an ROI."""
    # Check that the ROI calc signals exist
    assert isinstance(vortex.roi_sums.roi0, OphydObject)
    # Set some fake ROI values
    vortex.mcas.mca0.rois.roi0.count.sim_put(5)
    assert vortex.roi_sums.roi0.count.get() == 5
    vortex.mcas.mca0.rois.roi0.net_count.sim_put(13)
    assert vortex.roi_sums.roi0.net_count.get() == 13


@pytest.mark.parametrize("vortex", DETECTORS, indirect=True)
def test_mca_calcs(vortex):
    # Check that the ROI calc signals exist
    assert isinstance(vortex.mcas.mca0.total_count, OphydObject)
    # Does it sum together the total counts?
    spectrum = np.random.randint(2**16, size=(vortex.num_rois))
    mca = vortex.mcas.mca0
    mca.spectrum.sim_put(spectrum)
    assert mca.total_count.get(use_monitor=False) == np.sum(spectrum)


def test_default_time_signal_dxp(dxp):
    assert dxp.default_time_signal is dxp.preset_real_time


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
