import pytest

from epics import caget
from haven.instrument.fluorescence_detector import XspressDetector


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


@pytest.mark.xfail
def test_with_plan(vortex):
    ...
