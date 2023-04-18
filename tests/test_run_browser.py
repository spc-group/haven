from unittest.mock import MagicMock
from collections import namedtuple

from qtpy.QtCore import Qt

from firefly.main_window import PlanMainWindow
from firefly.run_browser import RunBrowserDisplay


def test_run_viewer_action(qtbot, ffapp, sim_tiled):
    ffapp.show_run_browser_action.trigger()
    assert isinstance(ffapp.windows["run_browser"], PlanMainWindow)


Node = namedtuple("Node", ("metadata",))


def test_load_runs(qtbot, ffapp, sim_tiled):
    client = {

    }
    display = RunBrowserDisplay()
    assert display.runs_model.rowCount() > 0


def test_metadata(qtbot, ffapp, sim_tiled):
    display = RunBrowserDisplay()
    # Change the proposal item
    selection_model = display.ui.run_tableview.selectionModel()
    item = display.runs_model.item(0, 1)
    assert item is not None
    rect = display.run_tableview.visualRect(item.index())
    with qtbot.waitSignal(display.runs_selected):
        qtbot.mouseClick(
            display.run_tableview.viewport(), Qt.LeftButton, pos=rect.center()
        )
    # Check that the metadata was set properly in the Metadata tab
    metadata_doc = display.ui.metadata_textedit.document()
    text = display.ui.metadata_textedit.document().toPlainText()
    assert "xafs_scan" in text
