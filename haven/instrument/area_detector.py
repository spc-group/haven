from apstools.devices import CamMixin_V34
from apstools.devices import SingleTrigger_V34
from ophyd import ADComponent, Component as Cpt, EpicsSignalRO
from ophyd import DetectorBase
from ophyd import SimDetectorCam
from ophyd import Lambda750kCam
from ophyd import SingleTrigger
from ophyd import Device, Kind
from ophyd.areadetector.filestore_mixins import FileStoreHDF5IterativeWrite
from ophyd.areadetector.plugins import HDF5Plugin_V34, HDF5Plugin_V31
from ophyd.areadetector.plugins import ImagePlugin_V34, ImagePlugin_V31
from ophyd.areadetector.plugins import PvaPlugin_V34, PvaPlugin_V31
from ophyd.areadetector.plugins import TIFFPlugin_V31
from ophyd.areadetector.plugins import ROIStatPlugin_V31, ROIStatPlugin_V34
from ophyd.areadetector.plugins import ROIPlugin_V31
from ophyd.areadetector.plugins import StatsPlugin_V31


from .._iconfig import load_config
from .instrument_registry import registry
from .. import exceptions


class SimDetectorCam_V34(CamMixin_V34, SimDetectorCam):
    ...


class StageCapture():
    """Mixin to prepare NDPlugin file capture mode.

    Sets the number of captures to zero (infinite), and starts
    capturing. Then when the device gets unstaged, capturing turns
    back off.

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Stage the capture button as well
        self.stage_sigs[self.capture] = 1
        self.stage_sigs[self.num_capture] = 0
    
    
class MyHDF5Plugin(FileStoreHDF5IterativeWrite, HDF5Plugin_V34):
    """
    Add data acquisition methods to HDF5Plugin.
    * ``stage()`` - prepare device PVs befor data acquisition
    * ``unstage()`` - restore device PVs after data acquisition
    * ``generate_datum()`` - coordinate image storage metadata
    """

    def stage(self):
        self.stage_sigs.move_to_end("capture", last=True)
        super().stage()


class SimDetector(SingleTrigger_V34, DetectorBase):
    """
    ADSimDetector
    SingleTrigger:
    * stop any current acquisition
    * sets image_mode to 'Multiple'
    """
        
    cam = ADComponent(SimDetectorCam_V34, "cam1:")
    image = ADComponent(ImagePlugin_V34, "image1:")
    pva = ADComponent(PvaPlugin_V34, "Pva1:")
    hdf1 = ADComponent(
        type("HDF5Plugin", (StageCapture, HDF5Plugin_V34), {}),
        "HDF1:",
        #write_path_template="/tmp/",
        #read_path_template=READ_PATH_TEMPLATE,
    )


class StatsPlugin(StatsPlugin_V31):
    _default_read_attrs = ["max_value", "min_value",
                           "min_xy.x", "max_xy.x",
                           "min_xy.y", "max_xy.y",
                           "total", "net",
                           "mean_value", "sigma_value",
    ]


class Lambda250K(SingleTrigger, DetectorBase):
    """
    A Lambda 250K area detector device.
    """
    cam = ADComponent(Lambda750kCam, "cam1:")
    image = ADComponent(ImagePlugin_V31, "image1:")
    pva = ADComponent(PvaPlugin_V31, "Pva1:")
    tiff = ADComponent(
        type("TIFFPlugin", (StageCapture, TIFFPlugin_V31), {}),
        "TIFF1:")
    hdf1 = ADComponent(
        type("HDF5Plugin", (StageCapture, HDF5Plugin_V31), {}),
        "HDF1:")
    roi1 = ADComponent(ROIPlugin_V31, "ROI1:", kind=Kind.config)
    roi2 = ADComponent(ROIPlugin_V31, "ROI2:", kind=Kind.config)
    roi3 = ADComponent(ROIPlugin_V31, "ROI3:", kind=Kind.config)
    roi4 = ADComponent(ROIPlugin_V31, "ROI4:", kind=Kind.config)
    stats1 = ADComponent(StatsPlugin, "Stats1:", kind=Kind.normal)
    stats2 = ADComponent(StatsPlugin, "Stats2:", kind=Kind.normal)
    stats3 = ADComponent(StatsPlugin, "Stats3:", kind=Kind.normal)
    stats4 = ADComponent(StatsPlugin, "Stats4:", kind=Kind.normal)
    stats5 = ADComponent(StatsPlugin, "Stats5:", kind=Kind.normal)
    
    _default_read_attrs = ["stats1", "stats2", "stats3", "stats4", "stats5"]


def load_area_detectors(config=None):
    if config is None:
        config = load_config()
    # Create the area detectors defined in the configuration
    for name, adconfig in config["area_detector"].items():
        DeviceClass = globals().get(adconfig["device_class"])
        # Check that it's a valid device class
        if DeviceClass is None:
            msg = f"area_detector.{name}.device_class={adconfig['device_class']}"
            raise exceptions.UnknownDeviceConfiguration(msg)
        # Create the device
        det = DeviceClass(prefix=f"{adconfig['prefix']}:",
                          name=name,
                          labels={"area_detectors"})
        registry.register(det)
