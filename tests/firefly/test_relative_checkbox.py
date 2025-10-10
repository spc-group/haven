import pytest

from firefly.plans.relative_checkbox import BLUE, RED, RelativeCheckbox


@pytest.fixture()
def checkbox(qtbot):
    cb = RelativeCheckbox()
    qtbot.addWidget(cb)
    return cb


def test_background_color(checkbox):
    assert BLUE in checkbox.styleSheet()
    checkbox.setChecked(True)
    assert RED in checkbox.styleSheet()
    checkbox.setChecked(False)
    assert BLUE in checkbox.styleSheet()


def test_is_relative(checkbox):
    assert not checkbox.relative
    checkbox.setChecked(True)
    assert checkbox.relative
    checkbox.setChecked(False)
    assert not checkbox.relative
