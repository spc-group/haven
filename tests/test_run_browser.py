from unittest.mock import MagicMock
from collections import namedtuple

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
