import asyncio

import pytest

from firefly.live_viewer import LiveViewerDisplay


@pytest.fixture()
def display(affapp, catalog, event_loop, mock):
    display = LiveViewerDisplay(root_node=catalog)
    display.clear_filters()
    # Flush pending async coroutines
    pending = asyncio.all_tasks(event_loop)
    event_loop.run_until_complete(asyncio.gather(*pending))
    assert all(task.done() for task in pending), "Init tasks not complete."
    # Yield displa to run the test
    try:
        yield display
    finally:
        pass
        # time.sleep(1)
        # # Cancel remaining tasks
        pending = asyncio.all_tasks(event_loop)
        event_loop.run_until_complete(asyncio.gather(*pending))
        assert all(task.done() for task in pending), "Shutdown tasks not complete."



def test_kafka_client(display):
    assert hasattr(display, "kafka_client")
