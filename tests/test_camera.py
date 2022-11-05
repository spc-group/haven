from haven import registry, load_config
from haven.instrument.camera import load_cameras


def test_load_cameras():
    load_cameras(config=load_config())
    # Check that cameras were registered
    cameras = registry.findall(label="cameras")
    assert len(cameras) == 1
