import pytest
from ophyd_async.core import TriggerInfo, set_mock_value

from haven.devices.detectors.ion_chamber_scaler import IonChamberScaler


@pytest.fixture()
def scaler(sim_registry):
    ion_chambers = {"I0": {"channel": 2}}
    scaler = IonChamberScaler(
        prefix="255idc:USBCTR0:",
        name="midstream_ion_chambers",
        ion_chambers=ion_chambers,
    )
    return scaler


@pytest.mark.xfail  # In development
@pytest.mark.asyncio
async def test_reading(scaler):
    await scaler.connect(mock=True)
    await scaler.prepare(TriggerInfo())
    set_mock_value(scaler.driver.clock_ticks, [2578])
    reading = await scaler.read()
    # Check that the correct readings are included
    assert f"{scaler.name}-elapsed_time" in reading
    assert f"{scaler.name}-current_channel" in reading
    assert f"{scaler.name}-clock_ticks" in reading
    assert reading[f"{scaler.name}-clock_ticks"]["value"] == 2578
    assert "I0-raw_counts" in reading
    assert "I0-counts" in reading
    assert "I0-voltage" in reading


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2026, UChicago Argonne, LLC
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
