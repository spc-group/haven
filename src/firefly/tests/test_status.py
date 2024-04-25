from pydm.widgets import PyDMByteIndicator
from qtpy.QtWidgets import QFormLayout 

from firefly.status import StatusDisplay

def test_shutter_controls(shutters, xia_shutter, sim_registry):
    """Do shutter controls get added to the window?"""
    disp = StatusDisplay()
    form = disp.ui.beamline_layout
    # Check label text
    label0 = form.itemAt(4, QFormLayout.LabelRole)
    assert "shutter" in label0.widget().text().lower()
    # Check the widgets for the shutter
    layout0 = form.itemAt(4, QFormLayout.FieldRole)
    indicator = layout0.itemAt(0).widget()
    assert isinstance(indicator, PyDMByteIndicator)
    open_btn = layout0.itemAt(1).widget()
    assert open_btn.text() == "Open"
    close_btn = layout0.itemAt(2).widget()
    assert close_btn.text() == "Close"
