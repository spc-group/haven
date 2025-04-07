import asyncio
import logging
from dataclasses import dataclass
from typing import Sequence

from bluesky_queueserver_api import BPlan
from ophyd_async.core import Device
from qasync import asyncSlot
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Signal

from firefly import display
from firefly.plans.util import is_valid_value

log = logging.getLogger()


units_mapping = {
    "degrees": "°",
    "micron": "µm",
    "microns": "µm",
    "um": "µm",
    "radian": "rad",
    "radians": "rad",
}


DEFAULT_PRECISION = 5


async def device_parameters(device: Device) -> dict:
    """Retrieve the relevant parameters from the selected device.

    - current value
    - limits
    - precision
    - units

    """
    # Retrieve parameters from the device
    try:
        aws = [device.read(), device.describe()]
        reading, desc = await asyncio.gather(*aws)
    except (AttributeError, TypeError):
        desc = {}
        value = 0
    else:
        desc = desc[device.name]
        value = reading[device.name]["value"]
    # Build into a new dictionary
    limits = desc.get("limits", {}).get("control", {})
    units = desc.get("units", "")
    units = units_mapping.get(units, units)
    return DeviceParameters(
        minimum=limits.get("low", float("-inf")),
        maximum=limits.get("high", float("inf")),
        current_value=value,
        precision=desc.get("precision", DEFAULT_PRECISION),
        units=units,
        is_numeric=desc.get("dtype", "number") == "number",
    )


@dataclass(frozen=True)
class DeviceParameters:
    minimum: float
    maximum: float
    current_value: float
    units: str
    precision: int
    is_numeric: bool


class RegionBase(QObject):
    widgets: Sequence[QtWidgets.QWidget]
    num_points_changed = Signal(int)

    def __init__(self, parent_layout: QtWidgets.QGridLayout, row: int):
        super().__init__()
        self.layout = parent_layout
        self.row = row
        self.setup_ui()

    async def setup_ui(self):
        raise NotImplementedError

    def remove(self):
        for widget in self.widgets:
            self.layout.removeWidget(widget)
            widget.deleteLater()


class PlanDisplay(display.FireflyDisplay):
    """Base class containing common functionality for basic plan window displays.
    Should be subclassed to produce a usable display.
    """

    plan_type: str
    scan_repetitions: int = 1
    scan_time_changed = Signal(float)
    total_time_changed = Signal(float)

    def customize_ui(self):
        self.ui.run_button.clicked.connect(self.queue_plan)

    async def _get_time(self, detector):
        """Get the dwell time value for a given detector."""
        time_signal = detector.default_time_signal
        if hasattr(time_signal, "get_value"):
            return await time_signal.get_value()
        return time_signal.get()

    def update_total_time(self):
        raise NotImplementedError

    def scan_durations(self, detector_time: float) -> tuple[float, float]:
        """Calculate the time needed for a single scan, and all scans.

        Placeholder for time calculation logic. Should be implemented
        in subclasses.


        Parameters
        ==========
        detector_time
          The time, in seconds, needed at each point for the
          detectors.

        Returns
        =======
        time_per_scan
          The time, in seconds, for each individual scan.
        total_time
          The time, in seconds, for all repeats of a scan.

        """
        raise NotImplementedError

    def get_meta_data(self):
        """Get metadata information."""
        md = {
            "sample_name": self.ui.lineEdit_sample.text(),
            "scan_name": self.ui.lineEdit_scan.text(),
            "purpose": self.ui.comboBox_purpose.currentText(),
            "notes": self.ui.textEdit_notes.toPlainText(),
            "sample_formula": self.ui.lineEdit_formula.text(),
        }
        # Only include metadata that isn't an empty string
        md = {key: val for key, val in md.items() if is_valid_value(val)}
        return md

    def plan_args(self):
        raise NotImplementedError

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        args, kwargs = self.plan_args()
        # Build the queue item
        item = BPlan(self.plan_type, *args, **kwargs)
        # Submit the item to the queueserver
        log.info(f"Adding {self.plan_type} plan to queue: {item}.")
        for i in range(self.scan_repetitions):
            self.queue_item_submitted.emit(item)


class RegionsDisplay(PlanDisplay, display.FireflyDisplay):
    """Contains variable number of plan parameter regions in a table.

    Should be subclassed to produce a usable display.

    Expects the subclass to have the following attributes:

    ui.regions_layout
      The vertical layout to receive the paramter regions.
    ui.num_motor_spin_box
      A spin box widget for how many regions to show.
    ui.run_button
      A button widget that will queue the plan.
    Region
      The object representing the region view to put into the layout.
    queue_plan
      A method that emits to `queue_item_submitted` signal with a plan
      item.

    """

    default_num_regions = 1
    Region = RegionBase
    regions: list[RegionBase]

    def customize_ui(self):
        super().customize_ui()
        self.reset_default_regions()
        # Disable the line edits in spin box (use up/down buttons instead)
        self.ui.num_regions_spin_box.lineEdit().setReadOnly(True)
        # Set up the mechanism for changing region number
        self.ui.num_regions_spin_box.valueChanged.connect(self.update_regions_slot)

    @asyncSlot(object)
    async def update_devices(self, registry):
        """Set available components in the motor boxes."""
        await super().update_devices(registry)
        await self.update_component_selector_devices(registry)
        if hasattr(self.ui, "detectors_list"):
            await self.ui.detectors_list.update_devices(registry)

    async def update_component_selector_devices(self, registry):
        """Update the devices for all the component selectors"""
        selectors = [region.motor_box for region in self.regions]
        aws = [box.update_devices(registry) for box in selectors]
        await asyncio.gather(*aws)

    def reset_default_regions(self):
        for region in getattr(self, "regions", ()):
            region.remove()
        self.regions = []
        for i in range(self.default_num_regions):
            self.add_region()
        self.ui.num_regions_spin_box.setValue(self.default_num_regions)

    def add_region(self):
        """Add a single row to the regions layout."""
        row = len(self.regions) + 1  # Include the header
        region = self.Region(self.ui.regions_layout, row=row)
        region.num_points_changed.connect(self.update_total_time)
        self.regions.append(region)
        return region

    def remove_region(self):
        region = self.regions.pop()
        region.remove()
        return region

    @asyncSlot(int)
    async def update_regions_slot(self, new_region_num):
        return await self.update_regions(new_region_num)

    async def update_regions(self, new_region_num: int):
        """Adjust regions from the scan params layout to reach
        *new_region_num*.

        """
        old_region_num = len(self.regions)
        # Only one of ``add`` or ``remove`` will have entries
        new_regions = [self.add_region() for i in range(old_region_num, new_region_num)]
        for i in range(new_region_num, old_region_num):
            self.remove_region()
        # Make sure new regions have device info
        await asyncio.gather(
            *[region.update_devices(self.registry) for region in new_regions]
        )
        return new_regions


# -----------------------------------------------------------------------------
# :author:    Juanjuan Huang, Mark Wolfman
# :email:     juanjuan.huang@anl.gov, wolfman@anl.gov
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
