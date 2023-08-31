from ophyd.sim import make_fake_device
from ophyd.device import do_not_wait_for_lazy_connection
from haven.instrument.xspress import Xspress3Detector


def test_num_elements(xspress):
    assert xspress.num_elements == 1

def test_num_rois(xspress):
    assert xspress.num_rois == 48
   

def test_mca_signals():
    xsp = Xspress3Detector("255id_xsp:", name="spcxsp")
    assert not xsp.connected
    # Spot-check some PVs
    with do_not_wait_for_lazy_connection(xsp.cam):
        assert xsp.cam.acquire_time._write_pv.pvname == "255id_xsp:det1:AcquireTime"
        assert xsp.cam.acquire._write_pv.pvname == "255id_xsp:det1:Acquire"
        assert xsp.cam.acquire._read_pv.pvname == "255id_xsp:det1:Acquire_RBV"
    assert xsp.mcas.mca1.rois.roi1.total_count._read_pv.pvname == "255id_xsp:MCA1ROI:1:Total_RBV"


def test_load_xspress(sim_registry, mocker):
    mocker.patch("ophyd.signal.EpicsSignalBase._ensure_connected")
    from haven.instrument.xspress import load_xspress
    load_xspress(config=None)
    vortex = sim_registry.find(name="vortex_me5")
    assert vortex.mcas.component_names == ("mca1", "mca2", "mca3", "mca4", "mca5")
