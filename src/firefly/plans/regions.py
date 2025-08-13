"""A base system for building a table of scan parameters.

The main class is the `RegionsManager`. Each plan window that needs a
region support should subclass `RegionsManager`, and then during
loading should instantiate this class with a QGridLayout() that will
hold the resulting widgets.

The core function is to manage `WidgetSet` objects and produce
`Region` objects.

`RegionsManager.WidgetSet` should be a dataclass that describes the
order of widgets. This will be useful for keeping track of the various
widgets in a given region.

`RegionsManager.Region` should describe the parameters selected by the
operator. This is the core output for the manager.

`RegionsManager.widgets_to_region` should convert a `WidgetSet` input
to a `Region` object.

"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, fields
from functools import partial
from typing import Any, Generator, cast

from ophyd_async.core import Device
from qasync import asyncSlot
from qtpy.QtCore import QObject, Qt, Signal
from qtpy.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGridLayout,
    QSpinBox,
    QWidget,
)

from firefly.exceptions import FireflyError


@dataclass(frozen=True)
class DeviceParameters:
    minimum: float
    maximum: float
    current_value: float
    units: str
    precision: int
    is_numeric: bool


async def device_parameters(device: Device) -> DeviceParameters:
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


def iter_widgets(
    widgets, include_checkbox: bool = False
) -> Generator[QWidget, Any, None]:
    """Iterate over all the widgets in a widget set.

    Parameters
    ----------
    include_checkbox
      If true, include the checkbox at the beginning of each row.
    """
    widgets_slice = slice(0, None) if include_checkbox else slice(1, None)
    _fields = fields(widgets)[widgets_slice]
    for field in _fields:
        widget = getattr(widgets, field.name)
        yield widget


units_mapping = {
    "degrees": "°",
    "deg": "°",
    "micron": "µm",
    "microns": "µm",
    "um": "µm",
    "radian": "rad",
    "radians": "rad",
}


DEFAULT_PRECISION = 5
HALF_SPACE = "\u202f"


async def update_device_parameters(
    device: Device, widgets: Sequence[QDoubleSpinBox | QSpinBox], is_relative: bool
):
    """Update the *widgets*' properties based on a *device*."""
    params = await device_parameters(device)
    set_limits(widgets=widgets, params=params, is_relative=is_relative)
    for widget in widgets:
        widget.setEnabled(params.is_numeric)
        widget.setEnabled(params.is_numeric)
        # Set other metadata
        widget.setDecimals(params.precision)
        # Handle units
        widget.setSuffix(f"{HALF_SPACE}{params.units}")
        # Set starting motor position
        if is_relative:
            widget.setValue(0)
        else:
            widget.setValue(params.current_value)


async def make_relative(
    device: Device, widgets: Sequence[QDoubleSpinBox | QSpinBox], is_relative: bool
):
    """Make *widgets* be relative to the *device* position."""
    params = await device_parameters(device)
    # Get last values first to avoid limit crossing
    if is_relative:
        new_positions = [widget.value() - params.current_value for widget in widgets]
    else:
        new_positions = [widget.value() + params.current_value for widget in widgets]
    # Update the current limits and positions
    set_limits(widgets=widgets, params=params, is_relative=is_relative)
    for widget, new_position in zip(widgets, new_positions):
        widget.setValue(new_position)


def set_limits(
    widgets: Sequence[QDoubleSpinBox | QSpinBox],
    params: DeviceParameters,
    is_relative: bool,
):
    """Set limits on the spin boxes to match the device limits."""
    # Determine new limits
    if is_relative:
        minimum = params.minimum - params.current_value
        maximum = params.maximum - params.current_value
    else:
        maximum, minimum = params.maximum, params.minimum
    # Update the widgets
    for widget in widgets:
        widget.setMaximum(maximum)
        widget.setMinimum(minimum)


class RegionsManager[WidgetsType](QObject):
    """Contains variable number of plan parameter regions in a table."""

    layout: QGridLayout
    header_rows = 1
    is_relative: bool

    # Qt signals
    regions_changed = Signal()

    # Over-ridable components
    # #######################

    @dataclass(frozen=True)
    class WidgetSet:
        active_checkbox: QCheckBox

    @dataclass(frozen=True, eq=True)
    class Region:
        is_active: bool

    # def widgets_to_region(self, widgets: WidgetSet) -> Region:
    #     """Take a list of widgets in a row, and build a Region object.

    #     This method is meant be over-ridden by subclasses.

    #     """
    #     return self.Region(is_active=widgets.active_checkbox.isChecked())

    async def create_row_widgets(self, row: int) -> list[QWidget]:
        """Create the widgets that are to go in each row, in order."""
        return []

    # Implementation details below, not meant to be sub-classed

    def __init__(self, *args, layout: QGridLayout, is_relative: bool = False, **kwargs):
        self.is_relative = is_relative
        self.layout = layout
        super().__init__(*args, **kwargs)

    def __iter__(self) -> Generator[Region, None, None]:
        for n in range(len(self)):
            yield self[n]

    def __getitem__(self, n: int) -> Region:
        # Check/fix the index
        if n < 0:
            n = len(self) + n
        if not (0 <= n < len(self)):
            raise IndexError("region index out of range")
        # Prepare the ``Region()`` object
        num_checkboxes = 1
        row = n + self.header_rows
        widgets = self.row_widgets(row=row)
        return self.widgets_to_region(widgets)

    def __len__(self):
        """Return the number of regions in the layout.

        This checks the layout's row count, but ensures each row
        actually has widgets.

        """
        layout = self.layout
        ncols = layout.columnCount()
        nrows = layout.rowCount()
        row_widgets = {
            row: [layout.itemAtPosition(row, col) for col in range(ncols)]
            for row in range(self.header_rows, nrows)
        }
        row_has_widgets = {
            row: any([widget is not None for widget in widgets])
            for row, widgets in row_widgets.items()
        }
        num_regions = sum(row_has_widgets.values())
        return num_regions

    async def add_row(self):
        """Add a single row to the regions layout.

        Each row includes a checkbox, and everything produced by
        `self.row_widgets()`.

        """
        row = len(self) + self.header_rows
        # Create a checkbox that will enable/disable the whole region
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(partial(self.enable_row_widgets, row=row))
        checkbox.stateChanged.connect(self.regions_changed)
        row_widgets = await self.create_row_widgets(row=row)
        widgets = [checkbox, *row_widgets]
        for column, widget in enumerate(widgets):
            self.layout.addWidget(widget, row, column, alignment=Qt.AlignTop)
        return row

    def remove_row(self):
        """Remove the last row of widgets from the layout."""
        row = len(self) + self.header_rows - 1
        for widget in iter_widgets(self.row_widgets(row), include_checkbox=True):
            self.layout.removeWidget(widget)
            widget.deleteLater()

    def row_widgets(self, row: int) -> WidgetsType:
        layout = self.layout
        items = [layout.itemAtPosition(row, col) for col in range(layout.columnCount())]
        widgets = [item.widget() if item is not None else item for item in items]
        if any([widget is None for widget in widgets]):
            raise FireflyError(
                f"Row {row} does not have a full list of widgets: {widgets}"
            )
        return cast(WidgetsType, self.WidgetSet(*widgets))

    @property
    def row_numbers(self):
        return range(self.header_rows, self.header_rows + len(self))

    def enable_all_rows(self, enabled: bool):
        """Enable/disable all rows in the layout."""
        for row in self.row_numbers:
            widgets = self.row_widgets(row)
            checkbox = widgets.active_checkbox  # type: ignore
            checkbox.setChecked(enabled)

    def enable_row_widgets(self, enabled: bool, *, row: int):
        """Enable/disable the widgets in a row of the layout.

        Excludes the checkbox used to enable/disable the rest of the
        row.

        """
        widgets = self.row_widgets(row)
        for widget in iter_widgets(widgets):
            widget.setEnabled(enabled)

    @asyncSlot(int)
    async def set_region_count(self, new_region_num: int):
        """Adjust regions from the scan params layout to reach
        *new_region_num*.

        """
        old_region_num = len(self)
        # Only one of ``add`` or ``remove`` will have entries
        new_regions = [
            (await self.add_row()) for i in range(old_region_num, new_region_num)
        ]
        old_regions = [self.remove_row() for i in range(new_region_num, old_region_num)]
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
