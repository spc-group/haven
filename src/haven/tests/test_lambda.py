import pytest

from haven.devices import LambdaDetector


@pytest.fixture()
async def detector():
    detector = LambdaDetector(prefix="255idLambda:", name="lambda_flex")
    await detector.connect(mock=True)
    # Registry with the simulated registry
    return detector


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


async def test_configuration(detector):
    """Confirm the device has the right signals."""
    config = await detector.read_configuration()
    assert "lambda_flex-driver-operating_mode" in config.keys()
    assert "lambda_flex-driver-dual_mode" in config.keys()
    assert "lambda_flex-driver-gating_mode" in config.keys()
    assert "lambda_flex-driver-charge_summing" in config.keys()
    assert "lambda_flex-driver-energy_threshold" in config.keys()
    assert "lambda_flex-driver-dual_threshold" in config.keys()


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
