import asyncio

import pytest
from ophyd_async.core import set_mock_value
from ophyd_async.testing import assert_value
from pydm.widgets import PyDMByteIndicator
from qtpy.QtWidgets import QFormLayout

from firefly.status import StatusDisplay
from haven.devices.shutter import ShutterState


@pytest.fixture()
async def display(qtbot, shutters, xia_shutter, sim_registry):
    display = StatusDisplay(shutter_check_period=0.05)
    qtbot.addWidget(display)
    await display.update_devices(sim_registry)
    try:
        yield display
    finally:
        # Stop it now, otherwise the timer runs until the display
        # object is garbage collected
        display.shutter_permit_timer.stop()


@pytest.mark.asyncio
async def test_shutter_widgets(display, shutters):
    """Do shutter control widgets get added to the window?"""
    form = display.ui.beamline_layout
    # Check label text
    first_shutter_row = 3
    label0 = form.itemAt(first_shutter_row, QFormLayout.LabelRole)
    assert "shutter" in label0.widget().text().lower()
    # Check the widgets for the shutter
    layout0 = form.itemAt(first_shutter_row, QFormLayout.FieldRole)
    indicator = layout0.itemAt(0).widget()
    assert isinstance(indicator, PyDMByteIndicator)
    open_btn = layout0.itemAt(1).widget()
    assert open_btn.text() == "Open"
    close_btn = layout0.itemAt(2).widget()
    assert close_btn.text() == "Close"


@pytest.mark.asyncio
async def test_shutter_controls(display, shutters, qtbot):
    """Do shutter controls actually move the shutter?"""
    form = display.ui.beamline_layout
    first_shutter_row = 3
    layout0 = form.itemAt(first_shutter_row, QFormLayout.FieldRole)
    shutterA = shutters[0]
    # Close the shutter and make sure it closed
    await assert_value(shutterA.readback, ShutterState.OPEN)
    close_btn = layout0.itemAt(2).widget()
    close_btn.click()
    await asyncio.sleep(0.01)
    await assert_value(shutterA.readback, ShutterState.CLOSED)
    # Open the shutter and make sure it opened again
    set_mock_value(shutterA.hutch_searched, True)
    set_mock_value(shutterA.aps_key, True)
    set_mock_value(shutterA.user_key, True)
    open_btn = layout0.itemAt(1).widget()
    open_btn.click()
    await asyncio.sleep(0.01)
    await assert_value(shutterA.readback, ShutterState.OPEN)


@pytest.mark.asyncio
async def test_shutter_controls_disabled(display, shutters, qtbot):
    """Do shutter controls get disabled when shutters can't be opened?"""
    shutterA, shutterB = shutters
    set_mock_value(shutterA.hutch_searched, True)
    set_mock_value(shutterA.aps_key, True)
    set_mock_value(shutterA.user_key, True)
    form = display.ui.beamline_layout
    # Check label text
    first_shutter_row = 3
    # Check the widgets for the shutter
    layout0 = form.itemAt(first_shutter_row, QFormLayout.FieldRole)
    open_btn = layout0.itemAt(1).widget()
    close_btn = layout0.itemAt(2).widget()
    # Shutter can be opened and closed
    await display.update_shutter_permissions()
    assert open_btn.isEnabled()
    assert close_btn.isEnabled()
    # Shutter can't be opened
    shutterA.movable_logic.allow_open = False
    await display.update_shutter_permissions()
    assert not open_btn.isEnabled()
    assert close_btn.isEnabled()
    # Shutter can't be closed
    shutterA.movable_logic.allow_close = False
    await display.update_shutter_permissions()
    assert not open_btn.isEnabled()
    assert not close_btn.isEnabled()


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
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
