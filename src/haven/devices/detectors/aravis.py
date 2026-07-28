from collections.abc import Sequence
from typing import Annotated as A

from ophyd_async.core import SignalR, SignalRW, SubsetEnum
from ophyd_async.epics.adaravis import AravisDriverIO as AravisDriverIOBase
from ophyd_async.epics.adaravis import (
    AravisTriggerLogic,
)
from ophyd_async.epics.adcore import (
    ADAcquireLogic,
    ADWriterFactory,
    AreaDetector,
    NDPluginBaseIO,
)
from ophyd_async.epics.core import PvSuffix

from .area_detectors import default_path_provider
from .image_plugin import NDPluginPva


class AravisTriggerSource(SubsetEnum):
    SOFTWARE = "Software"


class AravisDriverIO(AravisDriverIOBase):
    """Generic Driver supporting all GiGE cameras.

    This mirrors the interface provided by ADAravis/db/aravisCamera.template.
    """

    trigger_source: A[SignalRW[AravisTriggerSource], PvSuffix.rbv("TriggerSource")]


class AravisDetector(AreaDetector[AravisDriverIO]):
    _ophyd_labels_ = {"cameras", "detectors"}

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
        driver = AravisDriverIO(prefix + driver_suffix)
        super().__init__(
            driver,
            prefix,
            *writer_factories,
            acquire_logic=ADAcquireLogic(driver),
            trigger_logic=AravisTriggerLogic(driver),
            plugins=plugins,
            config_sigs=config_sigs,
            name=name,
        )
