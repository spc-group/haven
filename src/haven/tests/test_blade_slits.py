import pytest

from haven.devices import BladeSlits


@pytest.fixture()
async def slits():
    slits = BladeSlits("255idc:KB_slits", name="KB_slits")
    await slits.connect(mock=True)
    return slits


def test_signals(slits):
    """Test the PVs for the tweak forward/reverse."""
    assert slits.vertical.size.setpoint.source == "mock+ca://255idc:KB_slitsVsize.VAL"
    assert slits.vertical.size.readback.source == "mock+ca://255idc:KB_slitsVt2.C"
    assert (
        slits.vertical.center.setpoint.source == "mock+ca://255idc:KB_slitsVcenter.VAL"
    )
    assert slits.vertical.center.readback.source == "mock+ca://255idc:KB_slitsVt2.D"
    assert slits.horizontal.size.setpoint.source == "mock+ca://255idc:KB_slitsHsize.VAL"
    assert slits.horizontal.size.readback.source == "mock+ca://255idc:KB_slitsHt2.C"
    assert (
        slits.horizontal.center.setpoint.source
        == "mock+ca://255idc:KB_slitsHcenter.VAL"
    )
    assert slits.horizontal.center.readback.source == "mock+ca://255idc:KB_slitsHt2.D"


async def test_readback_name(slits):
    """Check that the readback has the same name as its parent."""
    assert slits.vertical.size.readback.name == "KB_slits-vertical-size"
    assert slits.vertical.size.setpoint.name == "KB_slits-vertical-size-setpoint"


async def test_readings(slits):
    reading = await slits.read()
    assert slits.vertical.size.readback.name in reading.keys()


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2025, UChicago Argonne, LLC
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
