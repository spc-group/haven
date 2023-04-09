from ophyd import DetectorBase

from haven import registry, load_config
from haven.instrument.camera import Camera, load_cameras


def test_load_cameras(ioc_camera):
    load_cameras(config=load_config())
    # Check that cameras were registered
    cameras = registry.findall(label="cameras")
    assert len(cameras) == 1
    assert isinstance(cameras[0], DetectorBase)


def test_camera_device(ioc_camera):
    camera = Camera(ioc_camera.prefix, name="camera")
    assert isinstance(camera, DetectorBase)
    assert hasattr(camera, "cam")
