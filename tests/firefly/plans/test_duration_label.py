import pytest
from scanspec.specs import Fly, Line

from firefly.plans.duration_label import Duration, DurationLabel, duration_from_spec

spec_times = [
    # Simple step line scan
    (2 @ Line("x", 0, 10, 6), Duration(livetime=6 * 2, movetime=10 / 0.5)),
    # Step line scan, backwards
    (2 @ Line("x", 10, 0, 6), Duration(livetime=6 * 2, movetime=10 / 0.5)),
    # Piece-wise step line scan
    (
        2 @ Line("x", 0, 6, 4).concat(Line("x", 8, 10, 2)),
        Duration(livetime=6 * 2, movetime=10 / 0.5),
    ),
    # Combined trajectory step line scan
    (
        2 @ Line("x", 0, 10, 6).zip(Line("y", 0, 10, 6)),
        Duration(livetime=6 * 2, movetime=10 / 0.5),
    ),
    # Fly line scan
    (Fly(2 @ Line("x", 0, 10, 6)), Duration(livetime=6 * 2, movetime=0)),
    # Grid step scan, no snaking
    (
        Line("y", -2, 2, 3) * (2 @ Line("x", 0, 10, 6)),
        Duration(livetime=36, movetime=5 * 4 * 3 + 2 * 10 / 0.5),
    ),
    # Grid step scan, with snaking
    (
        Line("y", -2, 2, 3) * (2 @ ~Line("x", 0, 10, 6)),
        Duration(livetime=36, movetime=5 * 4 * 3 + 2 * 2 / 0.5),
    ),
    # Grid fly scan, no snaking
    (
        Fly(Line("y", -2, 2, 3) * (2 @ Line("x", 0, 10, 6))),
        Duration(livetime=36, movetime=2 * 12 / 0.5),
    ),
    # Grid fly scan, with snaking
    (
        Fly(Line("y", -2, 2, 3) * (2 @ ~Line("x", 0, 10, 6))),
        Duration(livetime=36, movetime=2 * 2 / 0.5),
    ),
]


velocities = {
    "x": 0.5,
    "y": 0.5,
}


@pytest.mark.parametrize("spec,expected_duration", spec_times)
def test_duration_from_scanspec(spec, expected_duration):
    duration = duration_from_spec(spec, velocities=velocities)
    assert duration == expected_duration


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
