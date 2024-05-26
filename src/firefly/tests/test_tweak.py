import pytest

from firefly.tweak import TweakDisplay


@pytest.fixture()
def display(ffapp):
    disp = TweakDisplay()
    return disp


def test_value_updates_button_steps(display):
    display.ui.value_spin_box.setValue(6.28)
    assert display.ui.reverse_button.pressValue == "-6.28"
    assert display.ui.forward_button.pressValue == "6.28"
