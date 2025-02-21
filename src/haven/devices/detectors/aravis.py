from ophyd_async.core import PathProvider, SubsetEnum
from ophyd_async.epics.adaravis import AravisDetector as AravisDetectorBase
from ophyd_async.epics.core import epics_signal_rw_rbv

from .area_detectors import default_path_provider
from .image_plugin import ImagePlugin
from .overlay import OverlayPlugin



class AravisTriggerSource(SubsetEnum):
    SOFTWARE = "Software"
    LINE1 = "Line1"


class AutoGainMode(SubsetEnum):
    OFF = "Off"
    ONCE = "Once"
    CONTINUOUS = "Continuous"


class AravisDetector(AravisDetectorBase):
    _ophyd_labels_ = {"cameras", "detectors"}

    def __init__(
        self, prefix, *args, path_provider: PathProvider | None = None, **kwargs
    ):
        if path_provider is None:
            path_provider = default_path_provider()
        self.overlay = OverlayPlugin(f"{prefix}Over1:")
        self.pva = ImagePlugin(f"{prefix}Pva1:", protocol="pva")
        super().__init__(*args, prefix=prefix, path_provider=path_provider, **kwargs)
        # Replace a signal that has different enum options
        self.driver.trigger_source = epics_signal_rw_rbv(
            AravisTriggerSource,  # type: ignore
            f"{prefix}cam1:TriggerSource",
        )
        self.driver.gain_auto = epics_signal_rw_rbv(
            AutoGainMode,  # type: ignore
            f"{prefix}cam1:GainAuto",
        )
        self.set_name(self.name)
