import pytest
from bluesky_queueserver_api import BPlan

from firefly.devices.axilon_monochromator import AxilonMonochromatorDisplay


@pytest.fixture()
def display(qtbot, mono):
    display = AxilonMonochromatorDisplay(macros={"DEVICE": mono.name})
    qtbot.addWidget(display)
    return display


def test_title(display, mono):
    # display.customize_device()
    assert display.windowTitle() == "Monochromator"


async def test_calibrate_mono(qtbot, display, mono):
    await mono.connect(mock=True)
    display.ui.dial_spinbox.setValue(8720)
    display.ui.truth_spinbox.setValue(8730)
    # Click the set energy button
    expected_item = BPlan(
        "calibrate", "monochromator-energy", 8730, dial=8720, relative=True
    )

    def check_item(item):
        from pprint import pprint

        pprint(item.to_dict())
        pprint(expected_item.to_dict())
        return item.to_dict() == expected_item.to_dict()

    with qtbot.waitSignal(
        display.execute_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        display.queue_calibration()
