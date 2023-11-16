import pytest

from haven.instrument.xspress import Xspress3Detector


def test_num_elements(xspress):
    assert xspress.num_elements == 4


def test_num_rois(xspress):
    assert xspress.num_rois == 16


@pytest.mark.skip(
    reason="This test can't instantiate the device without having an IOC present"
)
def test_mca_signals():
    xsp = Xspress3Detector("255id_xsp:", name="spcxsp")
    assert not xsp.connected
    # Spot-check some PVs
    assert xsp.cam.acquire_time._write_pv.pvname == "255id_xsp:det1:AcquireTime"
    assert xsp.cam.acquire._write_pv.pvname == "255id_xsp:det1:Acquire"
    assert xsp.cam.acquire._read_pv.pvname == "255id_xsp:det1:Acquire_RBV"
    assert (
        xsp.mcas.mca0.rois.roi0.total_count._read_pv.pvname
        == "255id_xsp:MCA1ROI:1:Total_RBV"
    )


def test_roi_size(xspress):
    """Do the signals for max/size auto-update."""
    roi = xspress.mcas.mca0.rois.roi0
    roi.lo_chan.set(10).wait()
    # Update the size and check the maximum
    roi.size.set(7).wait()
    assert roi.hi_chan.get() == 17
    # Update the maximum and check the size
    roi.hi_chan.set(28).wait()
    assert roi.size.get() == 18
    # Update the minimum and check the size
    roi.lo_chan.set(25).wait()
    assert roi.size.get() == 3
