import time
from collections import OrderedDict

import numpy as np
import pytest
from ophyd import ADComponent as ADCpt
from ophyd.areadetector.cam import AreaDetectorCam
from ophyd.sim import instantiate_fake_device

from haven.instrument.area_detector import (
    DetectorBase,
    DetectorState,
    HDF5FilePlugin,
    load_area_detectors,
)


class Detector(DetectorBase):
    cam = ADCpt(AreaDetectorCam, "cam1:")
    hdf = ADCpt(HDF5FilePlugin, "HDF1:", write_path_template="/tmp/")


@pytest.fixture()
def detector(sim_registry):
    det = instantiate_fake_device(Detector)
    return det


def test_flyscan_kickoff(detector):
    detector.flyer_num_points.set(10)
    status = detector.kickoff()
    detector.cam.detector_state.sim_put(DetectorState.ACQUIRE)
    status.wait(timeout=3)
    assert status.success
    assert status.done
    # Check that the device was properly configured for fly-scanning
    assert detector.cam.acquire.get() == 1
    assert detector._fly_data == {}
    # Check that timestamps get recorded when new data are available
    detector.cam.array_counter.sim_put(1)
    event = detector._fly_data[detector.cam.array_counter]
    assert event[0].timestamp == pytest.approx(time.time())


def test_flyscan_complete(sim_ion_chamber):
    flyer = sim_ion_chamber
    # Run the complete method
    status = flyer.complete()
    status.wait(timeout=3)
    # Check that the detector is stopped
    assert flyer.stop_all._readback == 1


def test_flyscan_collect(sim_ion_chamber):
    flyer = sim_ion_chamber
    name = flyer.net_counts.name
    flyer.start_timestamp = 988.0
    # Make fake fly-scan data
    sim_data = np.zeros(shape=(8000,))
    sim_data[:6] = [3, 5, 8, 13, 2, 33]
    flyer.mca.spectrum._readback = sim_data
    sim_times = np.asarray([12.0e7, 4.0e7, 4.0e7, 4.0e7, 4.0e7, 4.0e7])
    flyer.mca_times.spectrum._readback = sim_times
    flyer.frequency.set(1e7).wait(timeout=3)
    # Ignore the first collected data point because it's during taxiing
    expected_data = sim_data[1:]
    # The real timestamps should be midway between PSO pulses
    flyer.timestamps = [1000, 1004, 1008, 1012, 1016, 1020]
    expected_timestamps = [1002.0, 1006.0, 1010.0, 1014.0, 1018.0]
    payload = list(flyer.collect())
    # Confirm data have the right structure
    for datum, value, timestamp in zip(payload, expected_data, expected_timestamps):
        assert datum == {
            "data": {name: [value]},
            "timestamps": {name: [timestamp]},
            "time": timestamp,
        }


def test_load_area_detectors(sim_registry):
    load_area_detectors()
    # Check that some area detectors were loaded
    dets = sim_registry.findall(label="area_detectors")


def test_hdf_dtype(detector):
    """Check that the right ``dtype_str`` is added to the image data to
    make tiled happy.
    """
    # Set up fake image metadata
    detector.hdf.data_type.sim_put("UInt8")
    original_desc = OrderedDict(
        [
            (
                "FakeDetector_image",
                {
                    "shape": (1, 1024, 1280),
                    "source": "PV:25idcARV4:",
                    "dtype": "array",
                    "external": "FILESTORE:",
                },
            )
        ]
    )
    # Update and check the description
    new_desc = detector.hdf._add_dtype_str(original_desc)
    assert new_desc["FakeDetector_image"]["dtype_str"] == "|u1"


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
