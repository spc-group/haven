from qtpy.QtCore import Qt

from firefly.detector_list import DetectorListView


def test_detector_model(ffapp, sim_registry, sim_vortex):
    view = DetectorListView()
    assert hasattr(view, "detector_model")
    assert view.detector_model.item(0).text() == "vortex_me4"


def test_selected_detectors(ffapp, sim_vortex, qtbot):
    """Do we get the list of detectors after they have been selected?"""
    # No detectors selected, so empty list
    view = DetectorListView()
    assert view.selected_detectors() == []
    # Select a detector and see if the selection updates
    selection_model = view.selectionModel()
    item = view.detector_model.item(0)
    assert item is not None
    rect = view.visualRect(item.index())
    with qtbot.waitSignal(view.selectionModel().selectionChanged):
        qtbot.mouseClick(view.viewport(), Qt.LeftButton, pos=rect.center())
    assert view.selected_detectors() == ["vortex_me4"]
