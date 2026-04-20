import pytest
import pytest_asyncio
from ophyd_async.core import (
    DetectorTrigger,
    StaticPathProvider,
    TriggerInfo,
    UUIDFilenameProvider,
    set_mock_value,
)
from ophyd_async.testing import assert_value

from haven.devices import LambdaDetector


@pytest_asyncio.fixture()
async def detector(tmp_path):
    path_provider = StaticPathProvider(
        filename_provider=UUIDFilenameProvider(),
        directory_path=tmp_path,
    )
    detector = LambdaDetector(
        prefix="255idLambda:", name="lambda_flex", path_provider=path_provider
    )
    await detector.connect(mock=True)
    # Registry with the simulated registry
    return detector


@pytest.mark.asyncio
async def test_signals(detector):
    """Confirm the device has the right signals."""
    assert (
        detector.driver.operating_mode.source
        == "mock+ca://255idLambda:cam1:OperatingMode_RBV"
    )
    assert detector.driver.dual_mode.source == "mock+ca://255idLambda:cam1:DualMode_RBV"
    assert (
        detector.driver.gating_mode.source
        == "mock+ca://255idLambda:cam1:GatingMode_RBV"
    )
    assert (
        detector.driver.charge_summing.source
        == "mock+ca://255idLambda:cam1:ChargeSumming_RBV"
    )
    assert (
        detector.driver.energy_threshold.source
        == "mock+ca://255idLambda:cam1:EnergyThreshold_RBV"
    )
    assert (
        detector.driver.dual_threshold.source
        == "mock+ca://255idLambda:cam1:DualThreshold_RBV"
    )


@pytest.mark.asyncio
async def test_configuration(detector):
    """Confirm the device has the right signals."""
    config = await detector.read_configuration()
    assert "lambda_flex-driver-operating_mode" in config.keys()
    assert "lambda_flex-driver-dual_mode" in config.keys()
    assert "lambda_flex-driver-gating_mode" in config.keys()
    assert "lambda_flex-driver-charge_summing" in config.keys()
    assert "lambda_flex-driver-energy_threshold" in config.keys()
    assert "lambda_flex-driver-dual_threshold" in config.keys()


@pytest.mark.asyncio
async def test_prepare_internal(detector):
    set_mock_value(detector.writer.file_path_exists, True)
    tinfo = TriggerInfo(collections_per_event=5, livetime=2.3, deadtime=0.2)
    await detector.prepare(tinfo)
    await assert_value(detector.driver.trigger_mode, "Internal")
    await assert_value(detector.driver.num_images, 5)
    await assert_value(detector.driver.image_mode, "Multiple")
    await assert_value(detector.driver.acquire_time, 2.3)
    await assert_value(detector.driver.acquire_period, 2.5)


@pytest.mark.asyncio
async def test_prepare_external(detector):
    set_mock_value(detector.writer.file_path_exists, True)
    tinfo = TriggerInfo(
        trigger=DetectorTrigger.EXTERNAL_EDGE,
        collections_per_event=5,
    )
    await detector.prepare(tinfo)
    await assert_value(detector.driver.trigger_mode, "External_ImagePer")
    await assert_value(detector.driver.num_images, 5)
    await assert_value(detector.driver.image_mode, "Multiple")


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
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
