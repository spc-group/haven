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


def test_scaler_prefix(qtbot, ffapp, sim_registry):
    """Make sure the scaler prefix gets passed in as a macro."""
    # Set up fake ion chamber
    window = FireflyMainWindow()
    ic = haven.IonChamber(
        "",
        scaler_prefix="255idcVME:scaler1",
        ch_num=1,
        name="my_ion_chamber",
        labels={"ion_chambers"},
    )
    sim_registry.register(ic)
    # Check the macros
    display = VoltmetersDisplay()
    assert display.macros()["SCALER"] == "255idcVME:scaler1"


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
    macros = disp.macros()
    assert macros == {"IC": "I0", "SCALER": "eggs_ioc"}
    # Check that a device has been created properly
    assert type(disp._device) is haven.IonChamber
