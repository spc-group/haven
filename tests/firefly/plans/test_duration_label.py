from firefly.plans.duration_label import DurationLabel


def test_duration_text(qtbot):
    label = DurationLabel()
    qtbot.addWidget(label)
    seconds = 16 * 3600 + 0 * 60 + 40
    label.set_seconds(seconds)
    assert label.text() == "16 h 0 m 40 s"


def test_duration_text_nan(qtbot):
    label = DurationLabel()
    qtbot.addWidget(label)
    label.set_seconds(float("nan"))
    assert label.text() == "– h – m – s"
