from unittest import mock

import pytest

from firefly.ion_chamber import IonChamberDisplay


@pytest.fixture()
async def display(ion_chamber, qtbot):
    display = IonChamberDisplay(macros={"IC": ion_chamber.name})
    qtbot.addWidget(display)
    display.launch_caqtdm = mock.MagicMock()
    return display


async def test_display(display):
    pass
