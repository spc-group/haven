from firefly.queue_button import QueueButton


def test_queue_button_style(queue_app):
    """Does the queue button change color/icon based."""
    btn = QueueButton()
    # Initial style should be disabled and plain
    assert not btn.isEnabled()
    assert btn.styleSheet() == ""
    # State when queue server is open and idle
    queue_state = {
        "worker_environment_exists": True,
        "items_in_queue": 0,
        "re_state": "idle",
    }
    queue_app.queue_status_changed.emit(queue_state)
    assert btn.isEnabled()
    assert "rgb(25, 135, 84)" in btn.styleSheet()
    assert btn.text() == "Run"
    # State when queue server is open and idle
    queue_state = {
        "worker_environment_exists": True,
        "items_in_queue": 0,
        "re_state": "running",
    }
    queue_app.queue_status_changed.emit(queue_state)
    assert btn.isEnabled()
    assert "rgb(0, 123, 255)" in btn.styleSheet()
    assert btn.text() == "Add to Queue"
