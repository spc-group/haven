import pytest
from bluesky import RunEngine
from bluesky import plan_stubs as bps
from bluesky import preprocessors as bpp
from ophyd_async.core import TriggerInfo, set_mock_value
from ophyd_async.testing import assert_value

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


@pytest.mark.xfail
@pytest.mark.asyncio
async def test_reading(scaler):
    await scaler.connect(mock=True)
    await scaler.prepare(TriggerInfo())
    set_mock_value(scaler.driver.clock_ticks_array, [2578])
    set_mock_value(scaler.driver.ion_chambers[2].raw_counts_array, [1337])
    reading = await scaler.read()
    # Check that the correct readings are included
    assert f"{scaler.name}-elapsed_time" in reading
    assert f"{scaler.name}-current_channel" in reading
    assert f"{scaler.name}-clock_ticks" in reading
    assert type(reading[f"{scaler.name}-clock_ticks"]["value"]) is int
    assert reading[f"{scaler.name}-clock_ticks"]["value"] == 2578
    assert "I0-raw_counts" in reading
    assert reading["I0-raw_counts"]["value"] == 1337
    assert type(reading["I0-raw_counts"]["value"]) is int
    assert "I0-counts" in reading
    assert reading["I0-counts"]["value"] == 1337
    assert type(reading["I0-counts"]["value"]) is int


@pytest.mark.xfail
async def test_collection(scaler):
    await scaler.connect(mock=True)
    # Run this in the run engine to make sure we don't collect stream assets
    RE = RunEngine({}, call_returns_result=True)

    docs = {}

    def stash_docs(name, doc):
        docs.setdefault(name, []).append(doc)

    RE.subscribe(stash_docs)

    @bpp.stage_decorator([scaler])
    @bpp.run_decorator()
    def dummy_fly_scan():
        yield from bps.prepare(scaler, TriggerInfo(), wait=True)
        yield from bps.declare_stream(scaler, name="the_stream")
        yield from bps.kickoff(scaler, wait=False, group="kickoff_group")
        set_mock_value(scaler.driver.acquiring, True)
        yield from bps.wait("kickoff_group")
        yield from bps.complete(scaler, wait=False, group="complete_group")
        set_mock_value(scaler.driver.current_channel, 1)
        set_mock_value(scaler.driver.acquiring, False)
        yield from bps.wait("complete_group")
        yield from bps.collect(scaler)

    RE(dummy_fly_scan())
    assert "event" in docs.keys()


async def test_calibration(scaler):
    await scaler.connect(mock=True)
    ion_chamber, *_ = scaler.driver.ion_chambers.values()
    set_mock_value(ion_chamber.raw_counts_array, [1234])
    set_mock_value(scaler.driver.clock_ticks_array, [100])
    await scaler.calibrate(truth=0)
    await assert_value(ion_chamber.calculation_expression, "B - 12.34 * A")


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
