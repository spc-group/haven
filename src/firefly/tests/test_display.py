from unittest.mock import AsyncMock, MagicMock

import pytest

from firefly.display import FireflyDisplay


@pytest.fixture()
def display(qtbot):
    # Load display
    display = FireflyDisplay()
    qtbot.addWidget(display)
    return display


def test_queue_item_submitted(display, qtbot):
    """Check that signals for submitted queue items route properly."""
    # No extra arguments
    test_item = MagicMock()

    def check_params(item, run_now):
        return item is test_item and run_now == False

    with qtbot.wait_signal(
        display.queue_item_submitted[object, bool],
        timeout=1000,
        check_params_cb=check_params,
    ):
        display.submit_queue_item(test_item)

    # Put on queue
    def check_params(item, run_now):
        return item is test_item and run_now == False

    with qtbot.wait_signal(
        display.queue_item_submitted[object, bool],
        timeout=1000,
        check_params_cb=check_params,
    ):
        display.submit_queue_item(test_item, run_now=False)

    # Execute immediately
    def check_params(item, run_now):
        return item is test_item and run_now == True

    with qtbot.wait_signal(
        display.queue_item_submitted[object, bool],
        timeout=1000,
        check_params_cb=check_params,
    ):
        display.submit_queue_item(test_item, run_now=True)
