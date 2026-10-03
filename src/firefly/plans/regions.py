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
import logging
from collections.abc import Sequence
from dataclasses import dataclass, fields
from functools import partial
from typing import Any, Generator, cast, get_args

from bluesky.protocols import Movable
from ophyd_async.core import Device, SignalDatatypeT
from qasync import asyncSlot
from qtpy.QtCore import QObject, Qt, Signal
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QSpinBox,
    QWidget,
)

from firefly.exceptions import FireflyError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceParameters:
    minimum: float
    maximum: float
    current_value: float
    units: str
    precision: int
    datatype: type
    is_movable: bool


def device_datatype(device: Device):
    # Figuring out the datatype to display is a little hacky
    # Straight signals have the datatype explicitly available
    if hasattr(device, "datatype"):
        return device.datatype
    # Compound devices can be trickier, maybe they use types exlicitly…
    bases = getattr(device, "__orig_bases__", ())
    possible_types = [dtype for cls in bases for dtype in get_args(cls)]
    # …but first we need to filter out generic types
    possible_types = [dtype for dtype in possible_types if dtype is not SignalDatatypeT]
    # And check if we have enough info to make a decision
    unique_types = set(possible_types)
    if len(unique_types) == 1:
        (datatype,) = unique_types
    else:
        datatype = Any
    return datatype


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
        desc = desc.get(device.name, {})
        value = reading.get(device.name, {}).get("value", None)
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
        is_movable=isinstance(device, Movable),
        datatype=device_datatype(device),
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
    for widget in widgets:
        widget.setEnabled(params.is_movable)
        is_float = isinstance(widget, QDoubleSpinBox)
        is_int = isinstance(widget, QSpinBox)
        if is_int or is_float:
            set_limits(widget=widget, params=params, is_relative=is_relative)
            # Handle units
            widget.setSuffix(f"{HALF_SPACE}{params.units}")

        if is_float:
            # Set other metadata
            widget.setDecimals(params.precision)
        # Set starting motor position
        if (is_float or is_int) and is_relative:
            widget.setValue(0)
        elif is_float or is_int:
            widget.setValue(params.current_value)
        elif isinstance(widget, QComboBox):
            # For enums, we look up the combobox item based on the
            # data not the name
            current_index = widget.findData(params.current_value)
            if current_index > -1:
                widget.setCurrentIndex(current_index)
        else:
            widget.setText(str(params.current_value))


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
    for widget, new_position in zip(widgets, new_positions):
        set_limits(widget=widget, params=params, is_relative=is_relative)
        widget.setValue(new_position)


def set_limits(
    widget: QDoubleSpinBox | QSpinBox,
    params: DeviceParameters,
    is_relative: bool,
):
    """Set limits on the spin boxes to match the device limits."""
    # Determine new limits
    if is_relative:
        try:
            minimum = params.minimum - params.current_value
            maximum = params.maximum - params.current_value
        except TypeError as exc:
            log.debug(f"Could not calculate relative limits: {exc}")
            return
    else:
        maximum, minimum = params.maximum, params.minimum
    # Integers can't handle infinity, so pick a really big/small int
    # instead
    if isinstance(widget, QSpinBox):
        maximum = int(min(maximum, 2147483647))
        minimum = int(max(minimum, -2147483648))
    else:
        maximum = float(maximum)
        minimum = float(minimum)
    widget.setMaximum(maximum)
    widget.setMinimum(minimum)


class RegionsManager[WidgetsType](QObject):
    """Contains variable number of plan parameter regions in a table."""

    layout: QGridLayout
    header_rows = 1
    is_relative: bool
    _device_registry = None

    # Qt signals
    regions_changed = Signal()
    parameters_changed = Signal()

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
        await self.update_devices(None, rows=[row])
        return row

    async def update_devices(self, registry=None, *arg, **kwargs):
        # Either use this registry, if given, or the last one we've seen
        if registry is None:
            registry = self._device_registry
        else:
            self._device_registry = registry
        if registry is None:
            log.info("Cannot set device widgets as no registry is available.")
        return registry

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
        # At most one of ``add`` or ``remove`` will have entries
        new_regions = [
            (await self.add_row()) for i in range(old_region_num, new_region_num)
        ]
        old_regions = [self.remove_row() for i in range(new_region_num, old_region_num)]

        if old_region_num != new_region_num:
            self.regions_changed.emit()
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
