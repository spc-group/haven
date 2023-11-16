from ophyd import DetectorBase

from haven import load_config, registry
from haven.instrument.camera import AravisDetector, load_cameras

PREFIX = "255idgigeA:"


def test_load_cameras():
    load_cameras(config=load_config())
    # Check that cameras were registered
    cameras = list(registry.findall(label="cameras"))
    assert len(cameras) == 1
    assert isinstance(cameras[0], DetectorBase)


def test_camera_device():
    camera = AravisDetector(PREFIX, name="camera")
    assert isinstance(camera, DetectorBase)
    assert hasattr(camera, "cam")


def test_camera_in_registry(sim_registry):
    camera = AravisDetector(PREFIX, name="camera")
    sim_registry.register(camera)
    # Check that all sub-components are accessible
    camera = sim_registry.find(camera.name)
    cam = sim_registry.find(f"{camera.name}_cam")
    gain = sim_registry.find(f"{camera.name}_cam.gain")
