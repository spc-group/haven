import pytest

from haven.devices.xspress import Xspress3Detector


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
