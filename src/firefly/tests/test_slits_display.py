import pytest

from firefly.slits import SlitsDisplay


@pytest.fixture()
def display(ffapp):
    disp = SlitsDisplay()
    return disp


def test_display_macros(display):
    # print(display)
    # assert False
    ...
