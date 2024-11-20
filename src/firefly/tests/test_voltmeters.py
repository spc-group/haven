import pytest
from bluesky_queueserver_api import BPlan
from pydm import widgets as PyDMWidgets
from pydm.widgets.analog_indicator import PyDMAnalogIndicator
from qtpy import QtWidgets

import haven
from firefly.voltmeters import VoltmetersDisplay
from haven.devices.ion_chamber import IonChamber


@pytest.fixture()
async def ion_chambers(sim_registry):
    devices = []
    for idx, name in enumerate(["I0", "It"]):
        ion_chamber = IonChamber(
            scaler_prefix="255idcVME:3820:",
            scaler_channel=idx,
            preamp_prefix=f"255idc:SR0{idx}",
            voltmeter_prefix="255idc:LJT7_Voltmeter0:",
            voltmeter_channel=idx,
            counts_per_volt_second=10e6,
            name=name,
        )
        await ion_chamber.connect(mock=True)
        sim_registry.register(ion_chamber)
        devices.append(ion_chamber)
    return devices


@pytest.fixture()
async def voltmeters_display(qtbot, ion_chambers, sim_registry):
    vms_display = VoltmetersDisplay()
    qtbot.addWidget(vms_display)
    await vms_display.update_devices(sim_registry)
    return vms_display


@pytest.mark.asyncio
async def test_rows(voltmeters_display):
    """Test that the voltmeters creates a new for each ion chamber."""
    vms_display = voltmeters_display
    # Check that the embedded display widgets get added correctly
    assert hasattr(vms_display, "_ion_chamber_rows")
    num_rows = len(vms_display._ion_chamber_rows)
    assert num_rows == 2
    # two displays and a separator
    expected_count = num_rows * 5
    assert vms_display.voltmeters_layout.count() == expected_count
    # Check that the rows have the correct widgets
    row = vms_display._ion_chamber_rows[0]
    assert isinstance(row.name_label, PyDMWidgets.PyDMLabel)
    assert isinstance(row.voltage_indicator, PyDMAnalogIndicator)
    assert isinstance(row.voltage_label, PyDMWidgets.PyDMLabel)
    assert isinstance(row.voltage_unit_label, QtWidgets.QLabel)
    assert isinstance(row.current_label, PyDMWidgets.PyDMLabel)
    assert isinstance(row.current_unit_label, QtWidgets.QLabel)
    assert isinstance(row.gain_down_button, PyDMWidgets.PyDMPushButton)
    assert isinstance(row.gain_up_button, PyDMWidgets.PyDMPushButton)
    assert isinstance(row.gain_value_label, PyDMWidgets.PyDMLabel)
    assert isinstance(row.gain_unit_label, PyDMWidgets.PyDMLabel)
    assert isinstance(row.auto_gain_checkbox, QtWidgets.QCheckBox)
    assert isinstance(row.details_button, QtWidgets.QPushButton)
    # Check that the widgets are added to the layouts
    assert row.name_label is row.column_layouts[0].itemAt(0).widget()
    assert row.voltage_indicator is row.column_layouts[1].itemAt(0).widget()
    assert row.voltage_label is row.column_layouts[2].itemAt(1).itemAt(1).widget()
    assert row.voltage_unit_label is row.column_layouts[2].itemAt(1).itemAt(2).widget()
    assert row.current_label is row.column_layouts[2].itemAt(2).itemAt(1).widget()
    assert row.current_unit_label is row.column_layouts[2].itemAt(2).itemAt(2).widget()
    assert row.column_layouts[3].itemAt(1).widget().text() == "Gain/Offset"
    assert row.gain_down_button is row.column_layouts[3].itemAt(2).itemAt(1).widget()
    assert row.gain_up_button is row.column_layouts[3].itemAt(2).itemAt(2).widget()
    assert row.gain_value_label is row.column_layouts[3].itemAt(3).itemAt(1).widget()
    assert row.gain_unit_label is row.column_layouts[3].itemAt(3).itemAt(2).widget()
    assert row.auto_gain_checkbox is row.column_layouts[4].itemAt(1).widget()
    # Check that a device has been created properly
    assert isinstance(row.device, haven.IonChamber)


@pytest.mark.asyncio
async def test_gain_button_hints(voltmeters_display, ion_chambers):
    """Test that the gain buttons get disabled when not usable."""
    row = voltmeters_display._ion_chamber_rows[0]
    ic = ion_chambers[0]
    assert row.gain_up_button.isEnabled()
    assert row.gain_down_button.isEnabled()
    # Now set the gain all the way to one limit
    row.update_gain_level_widgets(0)
    assert not row.gain_down_button.isEnabled()
    assert row.gain_up_button.isEnabled()
    # Now set the gain all the way to the other limit
    row.update_gain_level_widgets(27)
    assert row.gain_down_button.isEnabled()
    assert not row.gain_up_button.isEnabled()


def test_details_button(qtbot, voltmeters_display):
    """Check that the details button for each ion chamber triggers the global signal."""
    # Get an embedded display widget
    row = voltmeters_display._ion_chamber_rows[0]
    # Check that the signals are properly connected
    with qtbot.waitSignal(voltmeters_display.ui.details_window_requested, timeout=500):
        row.details_button.click()


@pytest.mark.asyncio
async def test_auto_gain_plan(voltmeters_display, qtbot):
    display = voltmeters_display
    # Put input values into the widgets
    display.ui.volts_min_line_edit.setText("")
    display.ui.volts_max_line_edit.setText("")
    # Check some boxes for which ion chambers get auto-gained
    for idx in [1]:
        row = display._ion_chamber_rows[idx]
        row.auto_gain_checkbox.setChecked(True)
    # Check that the correct plan was sent
    expected_item = BPlan("auto_gain", ["It"])

    def check_item(item):
        return item.to_dict() == expected_item.to_dict()

    # Click the run button and see if the plan is queued
    with qtbot.waitSignal(
        display.queue_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        # Simulate clicking on the auto_gain button
        display.ui.auto_gain_button.click()


def test_auto_gain_plan_with_args(qtbot, voltmeters_display):
    display = voltmeters_display
    # Put input values into the widgets
    display.ui.volts_min_line_edit.setText("1.0")
    display.ui.volts_max_line_edit.setText("4.5")
    # Check some boxes for which ion chambers get auto-gained
    for idx in [1]:
        ic_row = display._ion_chamber_rows[idx]
        ic_row.auto_gain_checkbox.setChecked(True)
    # Check that the correct plan was sent
    expected_item = BPlan("auto_gain", ["It"], volts_min=1.0, volts_max=4.5)

    def check_item(item):
        return item.to_dict() == expected_item.to_dict()

    # Click the run button and see if the plan is queued
    with qtbot.waitSignal(
        display.queue_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        # Simulate clicking on the auto_gain button
        display.ui.auto_gain_button.click()


@pytest.mark.asyncio
async def test_read_dark_current_plan(voltmeters_display, qtbot):
    display = voltmeters_display
    display.ui.shutter_checkbox.setChecked(True)
    # Check that the correct plan was sent
    expected_item = BPlan(
        "record_dark_current", ["I0", "It"], shutters=["experiment_shutter"]
    )

    def check_item(item):
        return item.to_dict() == expected_item.to_dict()

    # Click the run button and see if the plan is queued
    with qtbot.waitSignal(
        display.queue_item_submitted, timeout=1000, check_params_cb=check_item
    ):
        # Simulate clicking on the dark_current button
        # display.ui.dark_current_button.click()
        display.ui.record_dark_current()


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
