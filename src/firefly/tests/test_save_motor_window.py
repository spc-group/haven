import asyncio
import datetime as dt
import logging
from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from bluesky_queueserver_api import BPlan
from tiled.adapters.mapping import MapAdapter
from tiled.client import Context, from_context
from tiled.server.app import build_app

from firefly.plans.save_motor_window import MotorRegion, SaveMotorDisplay, TitleRegion
from firefly.tests.fake_position_runs import position_runs

log = logging.getLogger(__name__)

# Use a timezone we're not likely to be in for testing tz-aware behavior
fake_time = dt.datetime(2022, 8, 19, 19, 10, 51, tzinfo=ZoneInfo("Asia/Taipei"))


@pytest.fixture()
def client(mocker):
    tree = MapAdapter(position_runs)
    app = build_app(tree)
    with Context.from_app(app) as context:
        client = from_context(context)
        mocker.patch(
            "haven.motor_position.tiled_client", MagicMock(return_value=client)
        )
        yield client


@pytest.fixture()
async def display(qtbot, sim_registry, sync_motors, async_motors, dxp, ion_chamber):
    display = SaveMotorDisplay()
    qtbot.addWidget(display)
    await display.update_devices(sim_registry)
    display.ui.run_button.setEnabled(True)
    return display


@pytest.fixture
def mock_motor_positions():
    """Fixture to mock motor positions."""
    mock_position = MagicMock()
    mock_position.name = "TestPosition"
    mock_position.savetime = datetime.now().timestamp()
    mock_position.uid = "abc123"
    mock_position.motors = [
        MagicMock(name="motor1", readback=1.0, offset=0.0),
        MagicMock(name="motor2", readback=2.0, offset=0.1),
    ]
    return [mock_position]


@pytest.mark.asyncio
async def test_initialization(display):
    """Test that the SaveMotorDisplay initializes correctly."""
    assert display is not None
    assert isinstance(display, SaveMotorDisplay)
    assert display.title_region is not None
    assert isinstance(display.title_region, TitleRegion)
    assert len(display.regions) == display.default_num_regions
    for region in display.regions:
        assert isinstance(region, MotorRegion)


def test_on_regions_all_checkbox(display):
    """Test that checking/unchecking the regions_all_checkbox updates all regions."""
    title_region = display.title_region
    regions = display.regions

    # Uncheck the 'regions_all_checkbox'
    title_region.regions_all_checkbox.setChecked(False)
    for region in regions:
        assert not region.region_checkbox.isChecked()

    # Check the 'regions_all_checkbox'
    title_region.regions_all_checkbox.setChecked(True)
    for region in regions:
        assert region.region_checkbox.isChecked()


def test_get_scan_parameters(display):
    """Test that get_scan_parameters returns the correct motor names."""
    # Mock current_component to return a mock motor with a name
    for region in display.regions:
        mock_motor = MagicMock()
        mock_motor.name = "motor1"
        region.motor_box.current_component = MagicMock(return_value=mock_motor)
        region.region_checkbox.setChecked(True)

    motor_names = display.get_scan_parameters()
    assert motor_names == ["motor1"] * len(display.regions)


def test_queue_plan_no_name_provided(display, qtbot):
    """Test queue_plan when no name is provided."""
    # Mock get_scan_parameters to return motor names
    display.get_scan_parameters = MagicMock(return_value=["motor1"])
    display.ui.lineEdit_name.setText("")

    with qtbot.waitSignal(
        display.ui.textBrowser.textChanged, timeout=1000, raising=False
    ):
        display.queue_plan()

    assert "Please enter a name" in display.ui.textBrowser.toPlainText()


def test_on_region_checkbox(display):
    """Test that toggling a region's checkbox enables/disables the motor box and RBV label."""
    region = display.regions[0]
    # Uncheck the region checkbox
    region.region_checkbox.setChecked(False)
    assert not region.motor_box.isEnabled()
    assert not region.RBV_label.isEnabled()

    # Check the region checkbox
    region.region_checkbox.setChecked(True)
    assert region.motor_box.isEnabled()
    assert region.RBV_label.isEnabled()


@pytest.mark.asyncio
async def test_queue_plan_submission(display, monkeypatch):
    """Test that queue_plan submits the save_motor_position plan to the queue server."""
    # Mock get_scan_parameters
    display.ui.lineEdit_name.setText("TestPlan")

    await display.update_regions(2)
    monkeypatch.setattr(display, "submit_queue_item", mock.MagicMock())

    assert (
        len(display.regions) == 2
    ), f"Expected 2 regions, but got {len(display.regions)}"

    display.regions[0].motor_box.combo_box.setCurrentText("async_motor_1")
    display.regions[0].RBV_label.setText("12345.56789")

    display.regions[1].motor_box.combo_box.setCurrentText("async_motor_2")
    display.regions[1].RBV_label.setText("56789.0")

    display.queue_plan()

    expected_item = BPlan(
        "save_motor_position",
        "async_motor_1",
        "async_motor_2",
        name="TestPlan",
    )

    # Click the run button and see if the plan is queued
    display.queue_plan()
    assert display.submit_queue_item.called
    submitted_item = display.submit_queue_item.call_args[0][0]
    assert submitted_item.to_dict() == expected_item.to_dict()


@pytest.mark.asyncio
async def test_recall_motor_queue_plan_submission(display, monkeypatch):
    """Test that recall_motor_queue_plan submits the plan to the queue server."""
    # Mock get_current_selected_row
    display.get_current_selected_row = MagicMock(
        return_value=("Good position A", "a9b3e0fa-eba1-43e0-a38c-c7ac76278000")
    )
    monkeypatch.setattr(display, "submit_queue_item", mock.MagicMock())

    expected_item = BPlan(
        "recall_motor_position", uid="a9b3e0fa-eba1-43e0-a38c-c7ac76278000"
    )
    # Click the run button and see if the plan is queued
    display.recall_motor_queue_plan()
    assert display.submit_queue_item.called
    submitted_item = display.submit_queue_item.call_args[0][0]
    assert submitted_item.to_dict() == expected_item.to_dict()


@pytest.mark.asyncio
async def test_refresh_saved_position_list(qtbot, mock_motor_positions):
    """Test refreshing the saved positions list."""

    # Mock get_motor_positions to return an async generator of mock positions
    async def mock_get_motor_positions_impl(*args, **kwargs):
        for position in mock_motor_positions:
            yield position

    # Patch 'get_motor_positions' in the module where it's used
    with patch(
        "firefly.plans.save_motor_window.get_motor_positions",
        new=mock_get_motor_positions_impl,
    ):
        display = SaveMotorDisplay()
        qtbot.addWidget(display)
        table = display.ui.saved_positions_tableWidget

        # Manually call the refresh method
        await display.refresh_saved_position_list()

        # Ensure any pending tasks have completed
        await asyncio.sleep(1)

        print(f"Row count: {table.rowCount()}")
        for row in range(table.rowCount()):
            print(f"Row {row}:")
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    print(f"  Column {col}: {item.text()}")
                else:
                    print(f"  Column {col}: None")

        assert table.rowCount() == len(mock_motor_positions)
        for row, position in enumerate(mock_motor_positions):
            assert table.item(row, 0).text() == position.name
            savetime_str = datetime.fromtimestamp(position.savetime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            assert table.item(row, 1).text() == savetime_str
            assert table.item(row, 2).text() == position.uid


# -----------------------------------------------------------------------------
# :author:    Juanjuan Huang & Mark Wolfman
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
