from ophyd import DetectorBase

from haven import registry, load_config
from haven.instrument.camera import Camera, load_cameras


def test_load_cameras(ioc_camera):
    load_cameras(config=load_config())
    # Check that cameras were registered
    cameras = list(registry.findall(label="cameras"))
    assert len(cameras) == 1
    assert isinstance(cameras[0], DetectorBase)


def test_camera_device(ioc_camera):
    camera = Camera(ioc_camera.prefix, name="camera")
    assert isinstance(camera, DetectorBase)
    assert hasattr(camera, "cam")


def test_camera_in_registry(sim_registry, ioc_camera):
    camera = Camera(ioc_camera.prefix, name="camera")
    sim_registry.register(camera)
    # Check that all sub-components are accessible
    camera = sim_registry.find(camera.name)
    cam = sim_registry.find(f"{camera.name}_cam")
    gain = sim_registry.find(f"{camera.name}_cam.gain")
