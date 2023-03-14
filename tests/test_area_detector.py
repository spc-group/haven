from ophyd.device import do_not_wait_for_lazy_connection

from haven.instrument.area_detector import load_area_detectors

def test_load_area_detectors(sim_registry, ioc_area_detector):
    load_area_detectors({
        "area_detector": {
            "sim_det": {
                "prefix": "99idSimDet",
                "device_class": "SimDetector",
            }
        }
    })
    # Check that some area detectors were loaded
    dets = sim_registry.findall(label="area_detectors")
