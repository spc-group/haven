from haven.devices import SimDetector


def test_image_plugin():
    det = SimDetector("255idSimDet:")
    assert det.pva.image.source == "pva://255idSimDet:Pva1:Image"
