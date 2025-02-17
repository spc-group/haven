import pytest


from haven.devices import SimDetector


@pytest.fixture()
async def detector():
    det = SimDetector(name="sim_detector", prefix="255idSimDet:")
    await det.connect(mock=True)
    return det



def test_signals(detector):
    assert detector.driver.detector_state.source == "mock+ca://255idSimDet:cam1:DetectorState_RBV"
    assert detector.driver.acquire_time.source == "mock+ca://255idSimDet:cam1:AcquireTime_RBV"
    assert detector.driver.acquire.source == "mock+ca://255idSimDet:cam1:Acquire_RBV"
    # assert detector.driver.acquire_time_auto.source == "mock+ca://255idSimDet:cam1:AcquireTimeAuto"
    assert detector.fileio.array_size0.source == "mock+ca://255idSimDet:HDF1:ArraySize0_RBV"
    assert detector.fileio.array_size1.source == "mock+ca://255idSimDet:HDF1:ArraySize1_RBV"
    # Plugins
    assert detector.overlay.overlays[0].use.source == "mock+ca://255idSimDet:Over1:1:Use_RBV"
    assert detector.pva.image == "mock+ca://255idSimDet:..."
