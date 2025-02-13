from collections.abc import Sequence

from ophyd_async.core import PathProvider, SignalR
from ophyd_async.epics import adcore
from ophyd_async.epics.adcore import ADBaseController, AreaDetector
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw_rbv

from .area_detectors import default_path_provider


class EigerDriverIO(adcore.ADBaseIO):
    def __init__(self, prefix, name=""):
        # Detector information
        self.description = epics_signal_r(str, f"{prefix}Description_RBV")
        self.pixel_size_x = epics_signal_r(float, f"{prefix}XPixelSize_RBV")
        self.pixel_size_y = epics_signal_r(float, f"{prefix}YPixelSize_RBV")
        self.sensor_material = epics_signal_r(str, f"{prefix}SensorMaterial_RBV")
        self.sensor_thickness = epics_signal_r(float, f"{prefix}SensorThickness_RBV")
        self.dead_time = epics_signal_r(float, f"{prefix}DeadTime_RBV")
        # Detector status
        self.threshold_energy = epics_signal_rw_rbv(float, f"{prefix}ThresholdEnergy")
        self.photon_energy = epics_signal_rw_rbv(float, f"{prefix}PhotonEnergy")
        super().__init__(prefix=prefix, name=name)


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
        # Area detector IO devices
        driver = EigerDriverIO(f"{prefix}{drv_suffix}")
        controller = EigerController(driver)
        writer = writer_cls.with_io(
            prefix,
            path_provider=path_provider,
            dataset_source=driver,
            fileio_suffix=fileio_suffix,
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
