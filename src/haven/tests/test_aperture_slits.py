import pytest

from haven.devices import ApertureSlits


@pytest.fixture()
async def slits():
    slits = ApertureSlits(
        "255ida:slits:US:",
        name="whitebeam_slits",
    )
    await slits.connect(mock=True)
    return slits


def test_signals(slits):
    assert hasattr(slits, "horizontal")
    assert hasattr(slits.horizontal, "center")
    # Test pseudo motors controlled through the transform records
    assert (
        slits.horizontal.center.user_readback.source
        == "mock+ca://255ida:slits:US:hCenter.RBV"
    )
    assert (
        slits.vertical.center.user_readback.source
        == "mock+ca://255ida:slits:US:vCenter.RBV"
    )
    assert (
        slits.horizontal.size.user_readback.source
        == "mock+ca://255ida:slits:US:hSize.RBV"
    )
    assert (
        slits.vertical.size.user_readback.source
        == "mock+ca://255ida:slits:US:vSize.RBV"
    )
    # Check the derived signals are simple pass-throughs to the user readback/setpoint
    assert (
        slits.horizontal.size.readback.source == "mock+ca://255ida:slits:US:hSize.RBV"
    )
    assert (
        slits.horizontal.size.setpoint.source == "mock+ca://255ida:slits:US:hSize.VAL"
    )


async def test_readable(slits):
    reading = await slits.read()
    assert "whitebeam_slits-horizontal-center" in reading.keys()
    assert "whitebeam_slits-horizontal-size" in reading.keys()
    assert "whitebeam_slits-vertical-center" in reading.keys()
    assert "whitebeam_slits-vertical-size" in reading.keys()
    config = await slits.read_configuration()
    expected_config_signals = [
        "whitebeam_slits-vertical-size-offset_dir",
        "whitebeam_slits-vertical-size-description",
        "whitebeam_slits-vertical-size-offset",
        "whitebeam_slits-vertical-size-motor_egu",
        "whitebeam_slits-vertical-size-velocity",
        "whitebeam_slits-vertical-center-offset_dir",
        "whitebeam_slits-vertical-center-description",
        "whitebeam_slits-vertical-center-offset",
        "whitebeam_slits-vertical-center-motor_egu",
        "whitebeam_slits-vertical-center-velocity",
        "whitebeam_slits-horizontal-size-offset_dir",
        "whitebeam_slits-horizontal-size-description",
        "whitebeam_slits-horizontal-size-offset",
        "whitebeam_slits-horizontal-size-motor_egu",
        "whitebeam_slits-horizontal-size-velocity",
        "whitebeam_slits-horizontal-center-offset_dir",
        "whitebeam_slits-horizontal-center-description",
        "whitebeam_slits-horizontal-center-offset",
        "whitebeam_slits-horizontal-center-motor_egu",
        "whitebeam_slits-horizontal-center-velocity",
    ]
    assert sorted(list(config.keys())) == sorted(expected_config_signals)


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
