import asyncio
from pathlib import Path

import pytest
from ophyd_async.core import TriggerInfo, get_mock_put, set_mock_value

from haven.devices.detectors.dxp import DXPDetector

this_dir = Path(__file__).parent


@pytest.fixture()
async def detector():
    det = DXPDetector("255id_dxp:", name="vortex_me4")
    await det.connect(mock=True)
    set_mock_value(det.netcdf.file_path_exists, True)
    return det


def test_signals(detector):
    # Spot-check some PVs
    # SNL status records
    assert detector.drv.snl_connected.source == "mock+ca://255id_dxp:SNL_Connected"
    # Acquisition control records
    assert detector.drv.erase.source == "mock+ca://255id_dxp:EraseAll"
    assert detector.drv.start.source == "mock+ca://255id_dxp:StartAll"
    assert detector.drv.stop.source == "mock+ca://255id_dxp:StopAll"
    # Preset control records
    assert detector.drv.preset_mode.source == "mock+ca://255id_dxp:PresetMode"
    assert detector.drv.preset_live_time.source == "mock+ca://255id_dxp:PresetLive"
    assert detector.drv.preset_real_time.source == "mock+ca://255id_dxp:PresetReal"
    assert detector.drv.preset_events.source == "mock+ca://255id_dxp:PresetEvents"
    assert detector.drv.preset_triggers.source == "mock+ca://255id_dxp:PresetTriggers"
    # Status/statistics records
    assert detector.drv.status_scan_rate.source == "mock+ca://255id_dxp:StatusAll.SCAN"
    assert detector.drv.reading_scan_rate.source == "mock+ca://255id_dxp:ReadAll.SCAN"
    assert detector.drv.acquiring.source == "mock+ca://255id_dxp:Acquiring"
    assert detector.drv.elapsed_real_time.source == "mock+ca://255id_dxp:ElapsedReal"
    assert detector.drv.elapsed_live_time.source == "mock+ca://255id_dxp:ElapsedLive"
    assert detector.drv.accumulated_dead_time.source == "mock+ca://255id_dxp:DeadTime"
    assert (
        detector.drv.instantaneous_dead_time.source == "mock+ca://255id_dxp:IDeadTime"
    )
    # Low-level parameters
    assert (
        detector.drv.low_level_params_scan_rate.source
        == "mock+ca://255id_dxp:ReadLLParams.SCAN"
    )
    # Trace and diagnostic records
    assert (
        detector.drv.baseline_histograms_read_scan_rate.source
        == "mock+ca://255id_dxp:ReadBaselineHistograms.SCAN"
    )
    assert detector.drv.traces_scan_rate.source == "mock+ca://255id_dxp:ReadTraces.SCAN"
    assert (
        detector.drv.baseline_histogram_scan_rate.source
        == "mock+ca://255id_dxp:dxp1:BaselineHistogram.SCAN"
    )
    assert (
        detector.drv.trace_data_scan_rate.source
        == "mock+ca://255id_dxp:dxp1:TraceData.SCAN"
    )
    # Mapping mode control records
    assert detector.drv.collect_mode.source == "mock+ca://255id_dxp:CollectMode_RBV"
    # NetCDF file writer
    assert detector.netcdf.file_path.source == "mock+ca://255id_dxp:netCDF1:FilePath_RBV"
    assert detector.netcdf.file_name.source == "mock+ca://255id_dxp:netCDF1:FileName_RBV"
    assert detector.netcdf.file_path_exists.source == "mock+ca://255id_dxp:netCDF1:FilePathExists_RBV"
    assert detector.netcdf.file_template.source == "mock+ca://255id_dxp:netCDF1:FileTemplate_RBV"
    assert detector.netcdf.full_file_name.source == "mock+ca://255id_dxp:netCDF1:FullFileName_RBV"
    assert detector.netcdf.file_write_mode.source == "mock+ca://255id_dxp:netCDF1:FileWriteMode_RBV"
    assert detector.netcdf.num_capture.source == "mock+ca://255id_dxp:netCDF1:NumCapture_RBV"
    assert detector.netcdf.num_captured.source == "mock+ca://255id_dxp:netCDF1:NumCaptured_RBV"
    assert detector.netcdf.lazy_open.source == "mock+ca://255id_dxp:netCDF1:LazyOpen_RBV"
    assert detector.netcdf.capture.source == "mock+ca://255id_dxp:netCDF1:Capture_RBV"
    assert detector.netcdf.array_size0.source == "mock+ca://255id_dxp:netCDF1:ArraySize0_RBV"
    assert detector.netcdf.array_size1.source == "mock+ca://255id_dxp:netCDF1:ArraySize1_RBV"
    assert detector.netcdf.create_directory.source == "mock+ca://255id_dxp:netCDF1:CreateDirectory_RBV"    

async def test_config_signals(detector):
    desc = await detector.describe_configuration()
    print(desc)
    # assert False, "Write test for this"
    assert detector.drv.preset_mode.name in desc
    assert detector.drv.preset_live_time.name in desc
    assert detector.drv.preset_real_time.name in desc
    assert detector.drv.preset_events.name in desc
    assert detector.drv.preset_triggers.name in desc
    assert detector.drv.collect_mode.name in desc


async def test_prepare(detector):
    """These records should be set to SCAN="Passive" to avoid slowdowns:

    StatusAll
    ReadAll <- unless we're in mapping mode, then 2 sec
    ReadLLParams
    ReadBaselineHistograms
    ReadTraces
    dxp1:BaselineHistogram
    dxp1:TraceData

    collect_mode -> MCA spectra
    """
    await detector.prepare(TriggerInfo(number_of_triggers=1))


# async def test_trigger(detector):
#     trigger_info = TriggerInfo(number_of_triggers=1)
#     status = detector.trigger()
#     await asyncio.sleep(0.1)  # Let the event loop turn
#     set_mock_value(detector.hdf.num_captured, 1)
#     await status
#     # Check that signals were set
#     get_mock_put(detector.drv.num_images).assert_called_once_with(1, wait=True)


# async def test_stage(detector):
#     assert not get_mock_put(detector.drv.erase).called
#     await detector.stage()
#     get_mock_put(detector.drv.erase_on_start).assert_called_once_with(False, wait=True)
#     assert get_mock_put(detector.drv.erase).called


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
