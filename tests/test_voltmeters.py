from unittest import mock
import pytest
from qtpy import QtWidgets

from haven import IonChamber

from firefly.main_window import FireflyMainWindow
from firefly.application import FireflyApplication
from firefly.voltmeter import VoltmeterDisplay


@pytest.fixture
def app():
    yield FireflyApplication()


def test_device(app):
    window = FireflyMainWindow()
    display = VoltmeterDisplay(macros={"CHANNEL_NUMBER": 1})
    assert hasattr(display, "_device")
    assert isinstance(display._device, IonChamber)


def test_gain_button(app):
    # Fake ion chamber to make sure the gain was actually changed
    I0 = mock.MagicMock()
    assert not I0.increase_gain.called
    # Prepare the UI
    window = FireflyMainWindow()
    display = VoltmeterDisplay(device=I0)
    display._device = I0
    button = display.ui.gain_up_button
    # Check that the button is a button
    assert type(button) is QtWidgets.QPushButton
    assert hasattr(button, 'clicked')
    # Click the button and check that the gain changed
    button.click()
    assert I0.increase_gain.called


def test_current_display(app):
    """Test the labels that show the voltage converted to current
    based on amplifier settings.

    """
    display = VoltmeterDisplay(macros={"IOC_VME": "40idc", "CHANNEL_NUMBER": 1})
    assert hasattr(display, "_ch_gain_value")
    # Emit signals for changing the amplifier gain value
    display._ch_gain_value.value_slot(3)  # 10
    display._ch_gain_unit.value_slot(2)  # µA/V
    display._ch_voltage.value_slot(2.23)
    # Check that the label is updated
    assert display.gain == 10
    assert display.gain_unit == "µA"
    assert display.ui.ion_chamber_current.text() == "(0.223 µA)"
