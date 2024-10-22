from ophyd_async.epics.adsimdetector import SimDetector as SimDetectorBase

from .area_detectors import HavenDetector


class SimDetector(HavenDetector, SimDetectorBase):
    _ophyd_labels_ = {"area_detectors", "detectors"}
