from pathlib import Path
from unittest.mock import MagicMock

from firefly.action import WindowAction


def test_create_window(qtbot):
    action = WindowAction(
        name="start_queue",
        text="Start queue",
        display_file=Path(),
        WindowClass=MagicMock,
    )
    with qtbot.waitSignal(action.window_created):
        action.create_window()
