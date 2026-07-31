import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from ophyd_async.core import DetectorTriggerLogic, SignalR, derived_signal_r
from ophyd_async.epics.adcore import (
    ADAcquireLogic,
    ADBaseDataType,
    ADBaseIO,
    ADWriterFactory,
    AreaDetector,
    NDPluginBaseIO,
    prepare_exposures,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw_rbv

from .area_detectors import default_path_provider


def data_type_from_bit_depth(bit_depth: int) -> ADBaseDataType:
    """Decide on a numpy datatype based on bit depth.

    Assumes that the Eiger will always write unsigned data.

    """
    data_types = {
        8: ADBaseDataType.UINT8,
        16: ADBaseDataType.UINT16,
        32: ADBaseDataType.UINT32,
        64: ADBaseDataType.UINT64,
    }
    return data_types.get(bit_depth, ADBaseDataType.UNDEFINED)


class EigerDriverIO(ADBaseIO):
    def __init__(self, prefix, name=""):
        # Detector information
        self.description = epics_signal_r(str, f"{prefix}Description_RBV")
        self.pixel_size_x = epics_signal_r(float, f"{prefix}XPixelSize_RBV")
        self.pixel_size_y = epics_signal_r(float, f"{prefix}YPixelSize_RBV")
        self.sensor_material = epics_signal_r(str, f"{prefix}SensorMaterial_RBV")
        self.sensor_thickness = epics_signal_r(float, f"{prefix}SensorThickness_RBV")
        self.dead_time = epics_signal_r(float, f"{prefix}DeadTime_RBV")
        self.bit_depth = epics_signal_r(int, f"{prefix}BitDepthImage_RBV")
        # Detector status
        self.threshold_energy = epics_signal_rw_rbv(float, f"{prefix}ThresholdEnergy")
        self.photon_energy = epics_signal_rw_rbv(float, f"{prefix}PhotonEnergy")
        super().__init__(prefix=prefix, name=name)
        # Fixes a bug where the standard data type RBV PV is wrong
        old_name = self.data_type.name
        self.data_type = derived_signal_r(
            data_type_from_bit_depth, bit_depth=self.bit_depth
        )
        self.data_type.set_name(old_name)


@dataclass
class EigerTriggerLogic(DetectorTriggerLogic):
    driver: ADBaseIO

    def get_deadtime(self, exposure: float | None) -> float:
        # According to the manual, readout time is 3.00µs above 6.4
        # keV threshold energy. Set it to 10× to be safe.
        return 3e-5

    async def prepare_internal(
        self, num: int, livetime: float, deadtime: float
    ) -> None:
        await asyncio.gather(
            prepare_exposures(self.driver, num, livetime, deadtime),
        )


class EigerDetector(AreaDetector):
    """An Eiger area detector, e.g. Eiger 500K."""

    _ophyd_labels_ = {"detectors", "area_detectors"}

    def __init__(
        self,
        prefix: str,
        *writer_factories: ADWriterFactory,
        driver_suffix="cam1:",
        override_deadtime: float | None = None,
        plugins: dict[str, NDPluginBaseIO] | None = None,
        config_sigs: Sequence[SignalR] = (),
        name: str = "",
    ) -> None:
        if len(writer_factories) == 0:
            writer_factories = (
                ADWriterFactory.hdf(default_path_provider(), writer_suffix="HDF1:"),
            )
        # Area detector IO devices
        driver = EigerDriverIO(f"{prefix}{driver_suffix}")
        config_sigs = (
            driver.pixel_size_x,
            driver.pixel_size_y,
            driver.sensor_material,
            driver.sensor_thickness,
            driver.threshold_energy,
            driver.photon_energy,
            *config_sigs,
        )
        super().__init__(
            driver,
            prefix,
            *writer_factories,
            acquire_logic=ADAcquireLogic(driver),
            trigger_logic=EigerTriggerLogic(driver),
            plugins=plugins,
            config_sigs=config_sigs,
            name=name,
        )


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
