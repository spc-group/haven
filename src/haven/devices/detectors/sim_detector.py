from collections.abc import Sequence

from ophyd_async.core import SignalR
from ophyd_async.epics.adcore import (
    ADAcquireLogic,
    ADBaseIO,
    ADWriterFactory,
    AreaDetector,
    NDPluginBaseIO,
)
from ophyd_async.epics.adsimdetector import SimDetectorTriggerLogic

from .area_detectors import default_path_provider
from .image_plugin import NDPluginPva


class SimDetector(AreaDetector[ADBaseIO]):
    _ophyd_labels_ = {"area_detectors", "detectors"}

    def __init__(
        self,
        prefix: str,
        *writer_factories: ADWriterFactory,
        driver_suffix="cam1:",
        override_deadtime: float | None = None,
        plugins: dict[str, NDPluginBaseIO] = {},
        config_sigs: Sequence[SignalR] = (),
        name: str = "",
    ):
        if len(writer_factories) == 0:
            writer_factories = (
                ADWriterFactory.hdf(default_path_provider(), writer_suffix="HDF1:"),
            )
        plugins = {
            "pva": NDPluginPva(prefix=f"{prefix}Pva1:"),
            **plugins,
        }
        driver = ADBaseIO(prefix + driver_suffix)
        super().__init__(
            driver,
            prefix,
            *writer_factories,
            acquire_logic=ADAcquireLogic(driver),
            trigger_logic=SimDetectorTriggerLogic(driver),
            plugins=plugins,
            config_sigs=config_sigs,
            name=name,
        )
