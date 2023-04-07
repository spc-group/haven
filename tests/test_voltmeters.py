import time

from unittest import mock
import pytest
from qtpy import QtWidgets

import haven

from firefly.main_window import FireflyMainWindow
from firefly.application import FireflyApplication
from firefly.voltmeter import VoltmeterDisplay
from firefly.voltmeters import VoltmetersDisplay


def test_device(qtbot, ffapp, sim_registry):
    window = FireflyMainWindow()
    ic = haven.IonChamber("", ch_num=1, name="my_ion_chamber", labels={"ion_chambers"})
    sim_registry.register(ic)
    display = VoltmeterDisplay(macros={"IC": "my_ion_chamber"})
    assert hasattr(display, "_device")
    assert isinstance(display._device, haven.IonChamber)


def test_gain_button(qtbot, ffapp):
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
    assert hasattr(button, "clicked")
    # Click the button and check that the gain changed
    button.click()
    assert I0.increase_gain.called


def test_current_display(qtbot, ffapp):
    """Test the labels that show the voltage converted to current
    based on amplifier settings.

    """
    window = FireflyMainWindow()
    display = VoltmeterDisplay(macros={"IOC_VME": "40idc", "CHANNEL_NUMBER": 1})
    assert hasattr(display, "_ch_gain_value")
    # Emit signals for changing the amplifier gain value
    display._ch_gain_value.value_slot(3)  # 10
    display._ch_gain_unit.value_slot(2)  # µA/V
    display._ch_voltage.value_slot(2.23)
    # Check that the label is updated
    assert display.gain == 10
    assert display.gain_unit == "µA"
    assert display.ui.ion_chamber_current.text() == "(22.30 µA)"


def test_embedded_display_widgets(qtbot, sim_registry, ffapp):
    """Test the the voltmeters creates a new embedded display widget for
    each ion chamber.

    """
    window = FireflyMainWindow()
    # Set up fake ion chambers
    I0 = haven.IonChamber(
        prefix="eggs_ioc", ch_num=2, name="I0", labels={"ion_chambers"}
    )
    sim_registry.register(I0)
    It = haven.IonChamber(
        prefix="spam_ioc", ch_num=3, name="It", labels={"ion_chambers"}
    )
    sim_registry.register(It)
    # Load the display
    vms_display = VoltmetersDisplay()
    # Check that the embedded display widgets get added correctly
    assert hasattr(vms_display, "_ion_chamber_displays")
    assert len(vms_display._ion_chamber_displays) == 2
    assert vms_display.voltmeters_layout.count() == 2
    # Check that the embedded display widgets have the correct macros
    emb_disp = vms_display._ion_chamber_displays[0]
    disp = emb_disp.open_file(force=True)
    macros =  disp.macros()
    assert macros == {
        "IC": "I0"
    }
    # Check that a device has been created properly
    assert type(disp._device) is haven.IonChamber
