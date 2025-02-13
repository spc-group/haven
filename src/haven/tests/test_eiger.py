import pytest

from haven.devices.detectors.eiger import EigerDetector


@pytest.fixture()
async def eiger():
    detector = EigerDetector(prefix="255idEiger:", name="eiger")
    await detector.connect(mock=True)
    # Registry with the simulated registry
    return detector


async def test_signals(eiger):
    """Confirm the device has the right signals."""
    # for name, sig in eiger.driver.children():
    #     print(name.ljust(20), sig.source.split("/")[-1])
    # Detector information
    assert (
        eiger.driver.description.source == "mock+ca://255idEiger:cam1:Description_RBV"
    )
    assert (
        eiger.driver.pixel_size_x.source == "mock+ca://255idEiger:cam1:XPixelSize_RBV"
    )
    assert (
        eiger.driver.pixel_size_y.source == "mock+ca://255idEiger:cam1:YPixelSize_RBV"
    )
    assert (
        eiger.driver.sensor_material.source
        == "mock+ca://255idEiger:cam1:SensorMaterial_RBV"
    )
    assert (
        eiger.driver.sensor_thickness.source
        == "mock+ca://255idEiger:cam1:SensorThickness_RBV"
    )
    assert eiger.driver.dead_time.source == "mock+ca://255idEiger:cam1:DeadTime_RBV"
    # Detector status
    assert (
        eiger.driver.threshold_energy.source
        == "mock+ca://255idEiger:cam1:ThresholdEnergy_RBV"
    )
    assert (
        eiger.driver.photon_energy.source
        == "mock+ca://255idEiger:cam1:PhotonEnergy_RBV"
    )


async def test_configuration(eiger):
    """Confirm the device has the right signals."""
    config = await eiger.read_configuration()
    from pprint import pprint

    pprint(config)
    assert "eiger-driver-pixel_size_x" in config.keys()
    assert "eiger-driver-pixel_size_y" in config.keys()
    assert "eiger-driver-sensor_material" in config.keys()
    assert "eiger-driver-sensor_thickness" in config.keys()
    assert "eiger-driver-threshold_energy" in config.keys()
    assert "eiger-driver-photon_energy" in config.keys()


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
