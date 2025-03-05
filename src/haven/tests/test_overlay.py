import pytest

from haven.devices.detectors.overlay import OverlayPlugin


@pytest.fixture()
async def overlay():
    ovrly = OverlayPlugin(name="overlay", prefix="255idSimDet:Over1:")
    await ovrly.connect(mock=True)
    return ovrly


def test_signals(overlay):
    assert overlay.overlays[0].use.source == "mock+ca://255idSimDet:Over1:1:Use_RBV"
    assert overlay.overlays[0].description.source == "mock+ca://255idSimDet:Over1:1:Name_RBV"
    assert overlay.overlays[0].shape.source == "mock+ca://255idSimDet:Over1:1:Shape_RBV"
    assert overlay.overlays[0].draw_mode.source == "mock+ca://255idSimDet:Over1:1:DrawMode_RBV"
    assert overlay.overlays[0].red.source == "mock+ca://255idSimDet:Over1:1:Red_RBV"
    assert overlay.overlays[0].green.source == "mock+ca://255idSimDet:Over1:1:Green_RBV"
    assert overlay.overlays[0].blue.source == "mock+ca://255idSimDet:Over1:1:Blue_RBV"
    assert overlay.overlays[0].display_text.source == "mock+ca://255idSimDet:Over1:1:DisplayText_RBV"
    assert overlay.overlays[0].time_format.source == "mock+ca://255idSimDet:Over1:1:TimeStampFormat_RBV"
    assert overlay.overlays[0].font.source == "mock+ca://255idSimDet:Over1:1:Font_RBV"
    assert overlay.overlays[0].position_x.source == "mock+ca://255idSimDet:Over1:1:PositionX_RBV"
    assert overlay.overlays[0].center_x.source == "mock+ca://255idSimDet:Over1:1:CenterX_RBV"
    assert overlay.overlays[0].size_x.source == "mock+ca://255idSimDet:Over1:1:SizeX_RBV"
    assert overlay.overlays[0].width_x.source == "mock+ca://255idSimDet:Over1:1:WidthX_RBV"
    assert overlay.overlays[0].position_y.source == "mock+ca://255idSimDet:Over1:1:PositionY_RBV"
    assert overlay.overlays[0].center_y.source == "mock+ca://255idSimDet:Over1:1:CenterY_RBV"
    assert overlay.overlays[0].size_y.source == "mock+ca://255idSimDet:Over1:1:SizeY_RBV"
    assert overlay.overlays[0].width_y.source == "mock+ca://255idSimDet:Over1:1:WidthY_RBV"
