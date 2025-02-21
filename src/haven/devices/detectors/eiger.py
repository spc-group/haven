from collections.abc import Sequence

from ophyd_async.core import PathProvider, SignalR
from ophyd_async.epics import adcore
from ophyd_async.epics.adcore import ADBaseController, AreaDetector
from ophyd_async.epics.adcore._utils import ADBaseDataType, convert_ad_dtype_to_np
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw_rbv

from .area_detectors import default_path_provider
from .image_plugin import ImagePlugin
from .overlay import OverlayPlugin


class EigerDriverIO(adcore.ADBaseIO):
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


class EigerDatasetDescriber(adcore.ADBaseDatasetDescriber):
    """The datatype cannot be reliably determined from DataType_RBV.

    The Eiger always reports the data type as Int8, but this is never
    going to be correct. Instead, the data type can be inferred from
    the bit depth reported by the detector.

    """

    async def np_datatype(self) -> str:
        bit_depth = await self._driver.bit_depth.get_value()
        types = {
            8: ADBaseDataType.UINT8,
            16: ADBaseDataType.UINT16,
            32: ADBaseDataType.UINT32,
        }
        return convert_ad_dtype_to_np(types[bit_depth])


class EigerController(ADBaseController):
    def get_deadtime(self, exposure: float | None) -> float:
        raise NotImplementedError("Read deadtime from signal")


class EigerDetector(AreaDetector):
    """An Eiger area detector, e.g. Eiger 500K."""

    _ophyd_labels_ = {"detectors", "area_detectors"}

    def __init__(
        self,
        prefix: str,
        path_provider: PathProvider | None = None,
        drv_suffix="cam1:",
        writer_cls: type[adcore.ADWriter] = adcore.ADHDFWriter,
        fileio_suffix="HDF1:",
        name: str = "",
        config_sigs: Sequence[SignalR] = (),
        plugins: dict[str, adcore.NDPluginBaseIO] | None = None,
    ):
        if path_provider is None:
            path_provider = default_path_provider()
        # Other (non-data) area detector plugins
        self.overlay = OverlayPlugin(f"{prefix}Over1:")
        self.pva = ImagePlugin(f"{prefix}Pva1:", protocol="pva")
        # Area detector IO devices
        driver = EigerDriverIO(f"{prefix}{drv_suffix}")
        controller = EigerController(driver)
        fileio = adcore.NDFileHDFIO(f"{prefix}{fileio_suffix}")
        writer = writer_cls(
            fileio,
            path_provider=path_provider,
            name_provider=lambda: self.name,
            dataset_describer=EigerDatasetDescriber(driver),
            plugins=plugins,
        )
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
            controller=controller,
            writer=writer,
            plugins=plugins,
            name=name,
            config_sigs=config_sigs,
        )

    @property
    def default_time_signal(self):
        return self.driver.acquire_time


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
