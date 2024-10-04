from haven.devices import slits


def test_slits_tweak():
    """Test the PVs for the tweak forward/reverse."""
    slits_obj = slits.BladeSlits("255idc:KB_slits", name="KB_slits")
    # Check the inherited setpoint/readback PVs
    assert slits_obj.v.center.setpoint.pvname == "255idc:KB_slitsVcenter"
    assert slits_obj.v.center.readback.pvname == "255idc:KB_slitsVt2.D"
    # Check the tweak PVs
    assert (
        slits_obj.v.center.tweak_value.pvname == "255idc:KB_slitsVcenter_tweakVal.VAL"
    )
    assert slits_obj.v.center.tweak_reverse.pvname == "255idc:KB_slitsVcenter_tweak.A"
    assert slits_obj.v.center.tweak_forward.pvname == "255idc:KB_slitsVcenter_tweak.B"


def test_aperture_PVs():
    aperture = slits.ApertureSlits(
        "255ida:slits:US:",
        pitch_motor="m1",
        yaw_motor="m2",
        horizontal_motor="m3",
        diagonal_motor="m4",
        name="whitebeam_slits",
    )
    assert not aperture.connected
    assert hasattr(aperture, "h")
    assert hasattr(aperture.h, "center")
    # Test pseudo motors controlled through the transform records
    assert aperture.h.center.user_readback.pvname == "255ida:slits:US:hCenter.RBV"
    assert aperture.v.center.user_readback.pvname == "255ida:slits:US:vCenter.RBV"
    assert aperture.h.size.user_readback.pvname == "255ida:slits:US:hSize.RBV"
    assert aperture.v.size.user_readback.pvname == "255ida:slits:US:vSize.RBV"
    # Test real motors
    assert aperture.pitch.user_readback.pvname == "255ida:slits:m1.RBV"
    assert aperture.yaw.user_readback.pvname == "255ida:slits:m2.RBV"
    assert aperture.horizontal.user_readback.pvname == "255ida:slits:m3.RBV"
    assert aperture.diagonal.user_readback.pvname == "255ida:slits:m4.RBV"
    # Check the derived signals are simple pass-throughs to the user readback/setpoint
    assert aperture.h.size.readback._derived_from.pvname == "255ida:slits:US:hSize.RBV"
    assert aperture.h.size.setpoint._derived_from.pvname == "255ida:slits:US:hSize.VAL"


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
