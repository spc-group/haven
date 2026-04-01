import asyncio
from unittest.mock import call

import pytest
import pytest_asyncio
from ophyd_async.core import DetectorTrigger, TriggerInfo, set_mock_value
from ophyd_async.epics.adcore import ADImageMode
from ophyd_async.testing import assert_has_calls

from haven.devices.detectors.tetramm import BaseTetrAmmDetector


@pytest_asyncio.fixture()
async def tetramm():
    device = BaseTetrAmmDetector(prefix="255idTetra:QUAD1:", name="tetramm")
    await device.connect(mock=True)
    return device


@pytest.mark.asyncio
async def test_signals(tetramm):
    await tetramm.prepare(TriggerInfo())
    # reading = await tetramm.read()
    # assert reading == "READING"
    config = await tetramm.read_configuration()
    assert set(config.keys()) == {
        "tetramm-driver-acquire_mode",
        "tetramm-driver-bias_interlock",
        "tetramm-driver-bias_voltage",
        "tetramm-driver-bias_voltage_actual",
        "tetramm-driver-current_range",
        "tetramm-driver-firmware",
        "tetramm-driver-geometry",
        "tetramm-driver-model",
        "tetramm-driver-read_format",
        "tetramm-driver-sample_time",
        "tetramm-driver-trigger_mode",
        "tetramm-driver-trigger_polarity",
    }


@pytest.mark.asyncio
async def test_prepare_internal(tetramm):
    await tetramm.prepare(
        TriggerInfo(trigger=DetectorTrigger.INTERNAL, number_of_events=11)
    )
    assert_has_calls(
        tetramm.driver,
        [
            call.acquire_mode.put(ADImageMode.MULTIPLE),
            call.num_acquisitions.put(11),
        ],
    )


@pytest.mark.asyncio
async def test_trigger(tetramm):
    status = tetramm.trigger()
    await asyncio.sleep(0.01)
    set_mock_value(tetramm.driver.acquire, False)
    await status
    # assert_has_calls(
    #     tetramm.driver,
    #     [
    #         call.acquire_mode.put(ADImageMode.MULTIPLE),
    #         call.num_acquisitions.put(11),
    #     ],
    # )


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
