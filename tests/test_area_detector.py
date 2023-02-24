from haven.instrument.area_detector import load_area_detectors

def test_load_area_detectors(sim_registry):
    load_area_detectors()
    # Check that some area detectors were loaded
    # dets = sim_registry.findall(label="area_detectors")
