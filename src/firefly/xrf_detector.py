import json
import logging
import sys
from collections import defaultdict
from contextlib import contextmanager
from enum import IntEnum
from functools import partial
from pathlib import Path
from typing import Sequence

import numpy as np
import pydm
import pyqtgraph
import qtawesome as qta
from matplotlib.colors import TABLEAU_COLORS
from pydm.widgets import PyDMChannel, PyDMEmbeddedDisplay
from qtpy import uic
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QApplication, QWidget

from firefly import display
from haven import beamline

np.set_printoptions(threshold=sys.maxsize)


log = logging.getLogger(__name__)


pyqtgraph.setConfigOption("imageAxisOrder", "row-major")

colors = list(TABLEAU_COLORS.values())


class AcquireStates(IntEnum):
    DONE = 0
    ACQUIRING = 1


class ROIRegion(pyqtgraph.LinearRegionItem):
    """A selection on the XRF plot, showing the current ROI."""

    mca_num: int
    roi_num: int

    lo_channel: PyDMChannel
    hi_channel: PyDMChannel

    region_upper_changed = Signal(int)
    region_lower_changed = Signal(int)

    _last_upper: int = None
    _last_lower: int = None

    def __init__(self, address: str, *args, **kwargs):
        super().__init__(*args, swapMode="block", **kwargs)
        self.address = address
        # Set up channels to the IOC
        self.hi_channel = PyDMChannel(
            address=f"{address}.hi_chan",
            value_slot=self.set_region_upper,
            value_signal=self.region_upper_changed,
        )
        self.hi_channel.connect()
        self.lo_channel = PyDMChannel(
            address=f"{address}.lo_chan",
            value_slot=self.set_region_lower,
            value_signal=self.region_lower_changed,
        )
        self.lo_channel.connect()
        self.sigRegionChangeFinished.connect(self.handle_region_change)
        # Set initial display state
        self.setVisible(False)

    def handle_region_change(self):
        # Get new region boundary
        lower, upper = self.getRegion()
        lower = round(lower)
        upper = round(upper)
        if lower != self._last_lower:
            log.debug(f"Changing lower from {self._last_lower} to {lower}")
            if self._last_lower is not None:
                self.region_lower_changed.emit(lower)
            self._last_lower = lower
        if upper != self._last_upper:
            log.debug(f"Changing upper from {self._last_upper} to {upper}")
            if self._last_upper is not None:
                self.region_upper_changed.emit(upper)
            self._last_upper = upper

    def set_region_lower(self, new_lower):
        """Set the upper value of the highlighted region."""
        if new_lower == self._last_lower:
            return
        log.debug(
            f"Setting new region lower bound: {new_lower} from {self._last_lower}"
        )
        self._last_lower = new_lower
        self.blockLineSignal = True
        self.lines[0].setValue(new_lower)
        self.blockLineSignal = False

    def set_region_upper(self, new_upper):
        """Set the upper value of the highlighted region."""
        if new_upper == self._last_upper:
            return
        log.debug(
            f"Setting new region upper bound: {new_upper} from {self._last_upper}"
        )
        self._last_upper = new_upper
        self.blockLineSignal = True
        self.lines[1].setValue(new_upper)
        # self.setRegion(new_region)
        self.blockLineSignal = False


class XRF1DPlotItem(pyqtgraph.PlotItem):
    """The axes used for plotting."""

    hover_coords_changed = Signal(str)

    def hoverEvent(self, event):
        super().hoverEvent(event)
        if event.isExit():
            self.hover_coords_changed.emit("NaN")
            return
        # Get data coordinates from event
        pos = event.scenePos()
        data_pos = self.vb.mapSceneToView(pos)
        pos_str = f"({data_pos.x():.3f}, {data_pos.y():.3f})"
        self.hover_coords_changed.emit(pos_str)


class XRF1DPlotWidget(pyqtgraph.PlotWidget):
    """The inner widget containing just the plot."""

    def __init__(self, parent=None, background="default", plotItem=None, **kargs):
        plot_item = XRF1DPlotItem(**kargs)
        super().__init__(parent=parent, background=background, plotItem=plot_item)


class XRFPlotWidget(QWidget):
    """The outer widget, containing the plot and related controls."""

    ui_dir = Path(__file__).parent
    _data_items: defaultdict
    _selected_spectrum: int = None
    _region_items: dict
    device_name: str = ""
    target_mca: int = None

    # Signals
    plot_changed = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_items = defaultdict(lambda: None)
        self._region_items = {}
        self.ui = uic.loadUi(self.ui_dir / "xrf_plot.ui", self)
        # Create plotting items
        plot_item = self.ui.plot_widget.getPlotItem()
        plot_item.addLegend()
        plot_item.hover_coords_changed.connect(self.ui.coords_label.setText)

    def region(self, mca_num, roi_num):
        key = (mca_num, roi_num)
        plot_item = self.ui.plot_widget.getPlotItem()
        # Create a new region item if necessary
        if key not in self._region_items.keys():
            address = f"haven://{self.device_name}.mcas.mca{mca_num}.rois.roi{roi_num}"
            color = self.region_color(mca_num=mca_num, roi_num=roi_num)
            region = ROIRegion(
                address=address,
                brush=f"{color}10",
                hoverBrush=f"{color}20",
                pen=f"{color}50",
            )
            plot_item.addItem(region)
            self._region_items[key] = region
        # Return the region item
        return self._region_items[key]

    def handle_region_change(self, mca_num, roi_num, region):
        lower, upper = region.getRegion()
        lower = round(lower)
        upper = round(upper)
        self.lo_signal(mca_num=mca_num, roi_num=roi_num).emit(lower)
        self.hi_signal(mca_num=mca_num, roi_num=roi_num).emit(upper)

    def update_spectrum(self, mca_num, spectrum):
        """Plot the spectrum associated with the given MCA index."""
        # Create the plot item itself if necessary
        log.debug(f"New spectrum ({mca_num}): {repr(spectrum)}")
        show_spectrum = self.target_mca is None or mca_num == self.target_mca
        row, col = (0, 0)
        plot_item = self.ui.plot_widget.getPlotItem()
        # Get rid of the previous plots
        if (existing_item := self._data_items[mca_num]) is not None:
            plot_item.removeItem(existing_item)
        # Plot the spectrum
        if show_spectrum:
            try:
                length = len(spectrum)
            except TypeError:
                # Probably this means the spectrum is really just a scaler
                length = 1
                spectrum = np.asarray([spectrum])
            xdata = np.arange(length)
            color = self.spectrum_color(mca_num)
            self._data_items[mca_num] = plot_item.plot(
                xdata, spectrum, name=mca_num, pen=color
            )
            # Add region markers
            self.plot_changed.emit()

    def spectrum_color(self, mca_num):
        return colors[(mca_num) % len(colors)]

    def highlight_spectrum(self, mca_num, roi_num, hovered):
        """Highlight a spectrum and lowlight the rest.

        *mca_num* is the number (1-indexed) of the spectrum plotted.

        If *hovered* is true, then set the highlights, otherwise clear
        them.

        """
        raise NotImplementedError

    def show_region(self, show: bool, mca_num: int = 1, roi_num: int = 0):
        # Hide all the other regions
        for (mca, roi), region in self._region_items.items():
            region.setVisible(False)
        # Show/hide the specific region requested
        if show:
            log.debug(f"Showing region mca={mca_num} roi={roi_num}")
            self.region(mca_num=mca_num, roi_num=roi_num).setVisible(show)


class MCAPlotWidget(XRFPlotWidget):
    def region_color(self, mca_num, roi_num):
        return self.spectrum_color(mca_num)

    def highlight_spectrum(self, mca_num, roi_num, hovered):
        """Highlight a spectrum and lowlight the rest.

        *mca_num* is the number (1-indexed) of the spectrum plotted.

        If *hovered* is true, then set the highlights, otherwise clear
        them.

        """
        # Get the actual line plot
        solid, semisolid, transparent = (1.0, 0.55, 0.15)
        for key, data_item in self._data_items.items():
            if data_item is None:
                continue
            elif hovered:
                # Highlight this specific spectrum
                if key == mca_num:
                    opacity = solid
                elif key == self._selected_spectrum:
                    opacity = semisolid
                else:
                    opacity = transparent
                data_item.setOpacity(opacity)
            elif self._selected_spectrum is not None:
                # Highlight the spectrum that was previously selected
                log.debug(
                    "Reverting to previously selected spectrum:"
                    f" {self._selected_spectrum}"
                )
                is_dimmed = key != self._selected_spectrum
                if is_dimmed:
                    data_item.setOpacity(transparent)
                else:
                    data_item.setOpacity(solid)
            else:
                # Just make them all solid again
                data_item.setOpacity(solid)
        # Hide or unhide the selecting region
        is_selected = self._selected_spectrum is not None
        if hovered:
            self.show_region(show=True, mca_num=mca_num, roi_num=roi_num)
        elif is_selected:
            self.show_region(
                show=True, mca_num=self._selected_spectrum, roi_num=roi_num
            )
        else:
            self.show_region(show=False, mca_num=mca_num, roi_num=roi_num)

    def select_spectrum(self, mca_num, roi_num, is_selected):
        """Select an active spectrum to modify."""
        log.debug(f"Selecting spectrum {mca_num}")
        self._selected_spectrum = mca_num if is_selected else None
        self.highlight_spectrum(mca_num=mca_num, roi_num=roi_num, hovered=is_selected)


class ROIPlotWidget(XRFPlotWidget):
    def region_color(self, mca_num, roi_num):
        return colors[(roi_num) % len(colors)]

    def select_roi(self, mca_num, roi_num, is_selected):
        """Select an active spectrum to modify."""
        log.debug(f"Selecting ROI {roi_num}")
        self._selected_roi = roi_num if is_selected else None
        self.highlight_spectrum(mca_num=mca_num, roi_num=roi_num, hovered=is_selected)

    def highlight_spectrum(self, mca_num, roi_num, hovered):
        """Highlight a spectrum and lowlight the rest.

        *mca_num* is the number (1-indexed) of the spectrum plotted.

        If *hovered* is true, then set the highlights, otherwise clear
        them.

        """
        # Hide or unhide the selecting region
        is_selected = self._selected_roi is not None
        if hovered:
            self.show_region(show=True, mca_num=mca_num, roi_num=roi_num)
        elif is_selected:
            self.show_region(show=True, mca_num=mca_num, roi_num=self._selected_roi)
        else:
            self.show_region(show=False, mca_num=mca_num, roi_num=roi_num)


class ROIEmbeddedDisplay(PyDMEmbeddedDisplay):
    # Signals
    selected = Signal(bool)
    hovered = Signal(bool)

    def open_file(self, **kwargs):
        widget = super().open_file(**kwargs)
        # Connect signals if necessary
        if widget is not None:
            widget.selected.connect(self.selected)
        return widget

    def enterEvent(self, event=None):
        self.hovered.emit(True)

    def leaveEvent(self, event=None):
        self.hovered.emit(False)


class XRFDetectorDisplay(display.FireflyDisplay):
    caqtdm_ui_file = "/APSshare/epics/synApps_6_2_1/support/xspress3-2-5/xspress3App/opi/ui/xspress3_1chan.ui"

    roi_displays: Sequence = []
    mca_displays: Sequence = []
    _spectrum_channels: Sequence
    _selected_mca: int = None
    _mca_lower_receiver = None
    _mca_upper_receiver = None

    # Signals
    spectrum_changed = Signal(int, object)  # (MCA index, spectrum)
    mca_row_hovered = Signal(int, int, bool)  # (MCA num, roi_num, entered)
    roi_row_hovered = Signal(int, int, bool)  # (MCA num, roi_num, entered)

    def ui_filename(self):
        return "xrf_detector.ui"

    def customize_ui(self):
        device = self.device
        self.setWindowTitle(device.name)
        self.ui.mca_plot_widget.device_name = self.device.name
        self.ui.roi_plot_widget.device_name = self.device.name
        # Set ROI and element selection comboboxes
        self.ui.mca_combobox.currentIndexChanged.connect(self.draw_roi_widgets)
        self.ui.roi_combobox.currentIndexChanged.connect(self.draw_mca_widgets)
        elements = [str(i) for i in range(device.num_elements)]
        self.ui.mca_combobox.addItems(elements)
        rois = [str(i) for i in range(device.num_rois)]
        self.ui.roi_combobox.addItems(rois)
        # Controls for increment/decrement ROI/MCA combobox
        self.ui.mca_up_button.setIcon(qta.icon("fa5s.arrow-right"))
        self.ui.mca_down_button.setIcon(qta.icon("fa5s.arrow-left"))
        self.ui.roi_up_button.setIcon(qta.icon("fa5s.arrow-right"))
        self.ui.roi_down_button.setIcon(qta.icon("fa5s.arrow-left"))
        self.ui.mca_up_button.clicked.connect(
            partial(self.increment_combobox, combobox=self.ui.mca_combobox, step=1)
        )
        self.ui.mca_down_button.clicked.connect(
            partial(self.increment_combobox, combobox=self.ui.mca_combobox, step=-1)
        )
        self.ui.roi_up_button.clicked.connect(
            partial(self.increment_combobox, combobox=self.ui.roi_combobox, step=1)
        )
        self.ui.roi_down_button.clicked.connect(
            partial(self.increment_combobox, combobox=self.ui.roi_combobox, step=-1)
        )
        # Button for starting/stopping the detector
        self.ui.oneshot_button.setIcon(qta.icon("fa5s.camera"))
        # Buttons for modifying all ROI settings
        self.ui.mca_copyall_button.setIcon(qta.icon("fa5.clone"))
        self.ui.mca_copyall_button.clicked.connect(self.copy_selected_mca)
        self.ui.roi_copyall_button.setIcon(qta.icon("fa5.clone"))
        self.ui.roi_copyall_button.clicked.connect(self.copy_selected_roi)
        self.ui.mca_enableall_checkbox.setCheckState(Qt.PartiallyChecked)
        self.ui.mca_enableall_checkbox.stateChanged.connect(self.enable_mca_checkboxes)
        self.ui.roi_enableall_checkbox.setCheckState(Qt.PartiallyChecked)
        self.ui.roi_enableall_checkbox.stateChanged.connect(self.enable_roi_checkboxes)
        # Connect signals for when spectra change
        self.spectrum_changed.connect(self.ui.mca_plot_widget.update_spectrum)
        self.spectrum_changed.connect(self.ui.roi_plot_widget.update_spectrum)
        self.mca_row_hovered.connect(self.ui.mca_plot_widget.highlight_spectrum)
        self.roi_row_hovered.connect(self.ui.roi_plot_widget.highlight_spectrum)

    def launch_caqtdm(
        self,
    ):
        super().launch_caqtdm(macros={"P": self.device.prefix.strip(":")})

    def enable_mca_checkboxes(self, new_state):
        """Check/uncheck the hinting checkboxes in response to the
        "Enable all" checkbox.

        """
        is_checked = new_state == Qt.Checked
        log.debug(f"Setting all MCA elements enabled: {new_state} / {is_checked}")
        self.ui.mca_enableall_checkbox.setTristate(False)
        self.enable_row_checkboxes(displays=self.mca_displays, is_checked=is_checked)

    def enable_roi_checkboxes(self, new_state):
        is_checked = new_state == Qt.Checked
        log.debug(f"Setting all ROI elements enabled: {new_state} / {is_checked}")
        self.ui.roi_enableall_checkbox.setTristate(False)
        self.enable_row_checkboxes(displays=self.roi_displays, is_checked=is_checked)

    def enable_row_checkboxes(self, displays, is_checked):
        """Check/uncheck the hinting checkboxes in response to the "Enable
        all" checkbox.

        """
        for display in displays:
            try:
                checkbox = display.embedded_widget.ui.enabled_checkbox
                checkbox.setChecked(is_checked)
            except AttributeError:
                pass

    def copy_selected_row(self, displays, source_display):
        """Copy the name, upper limit, and lower limits from one ROI|MCA row
        to all the rest.

        Parameters
        ==========
        display
          A sequence of all the displays to copy to.
        source_display
          The embedded display for the row from which to copy.

        """
        new_label = source_display.embedded_widget.ui.label_lineedit.text()
        new_lower = source_display.embedded_widget.ui.lower_lineedit.text()
        new_upper = source_display.embedded_widget.ui.upper_lineedit.text()
        # Set all the other MCA rows with values from selected MCA row
        for display in displays:
            if display is not source_display:
                if display.embedded_widget is None:
                    continue
                display.embedded_widget.ui.label_lineedit.setText(new_label)
                display.embedded_widget.ui.lower_lineedit.setText(new_lower)
                display.embedded_widget.ui.upper_lineedit.setText(new_upper)
                # Send the new value over the wire
                for widget in [
                    display.embedded_widget.ui.label_lineedit,
                    display.embedded_widget.ui.lower_lineedit,
                    display.embedded_widget.ui.upper_lineedit,
                ]:
                    if widget._connected:
                        widget.send_value()

    def copy_selected_roi(self):
        """Copy the label, hi channel, and lo channel values from the selected
        ROI row to all other visible ROI rows.

        """
        log.debug(f"Copying ROI {self._selected_roi}")
        # Get existing values from selected ROI row
        roi_idx = self._selected_roi
        source_display = self.roi_displays[roi_idx]
        self.copy_selected_row(
            source_display=source_display, displays=self.roi_displays
        )

    def copy_selected_mca(self):
        """Copy the label, hi channel, and lo channel values from the selected
        MCA row to all other visible MCA rows.

        """
        log.debug(f"Copying MCA {self._selected_mca}")
        # Get existing values from selected MCA row
        mca_idx = self._selected_mca
        source_display = self.mca_displays[mca_idx]
        self.copy_selected_row(
            source_display=source_display, displays=self.mca_displays
        )

    def handle_new_spectrum(self, new_spectrum, mca_num):
        self.spectrum_changed.emit(mca_num, new_spectrum)

    def customize_device(self):
        # Load the device from the registry
        device_name = self.macros()["DEV"]
        self.device = device = beamline.registry.find(device_name)
        # Set up data channels
        self._spectrum_channels = []
        for mca_num in range(self.device.num_elements):
            address = f"haven://{device.name}.mcas.mca{mca_num}.spectrum"
            channel = pydm.PyDMChannel(
                address=address,
                value_slot=partial(self.handle_new_spectrum, mca_num=mca_num),
            )
            channel.connect()
            self._spectrum_channels.append(channel)

    def increment_combobox(self, combobox, step):
        n_items = combobox.count()
        new_index = (combobox.currentIndex() + step) % n_items
        combobox.setCurrentIndex(new_index)

    @contextmanager
    def disable_ui(self):
        widget = self
        # Disable to widgets
        widget.setEnabled(False)
        # Set waiting cursor
        old_cursor = self.cursor()
        self.setCursor(Qt.WaitCursor)
        # Update the UI
        QApplication.instance().processEvents()
        yield
        # Re-enabled everything
        widget.setEnabled(True)
        widget.setCursor(old_cursor)

    def roi_selected(self, is_selected: bool, roi_num=None):
        """Handler for when an ROI is selected for editing.

        Parameters
        ==========
        is_selected
          Will be true if the ROI was selected, or false if the ROI
          was deselected.

        """
        # Save the selected ROI number for later
        if is_selected:
            self._selected_roi = roi_num
        else:
            self._selected_roi = None
        # Set global controls for this ROI
        self.ui.roi_copyall_button.setEnabled(is_selected)
        # Disable the other rows
        for idx, disp in enumerate(self.roi_displays):
            if is_selected and idx != roi_num:
                disp.setEnabled(False)
            else:
                disp.setEnabled(True)
        # Show this spectrum highlighted in the plots
        mca_num = self.ui.mca_combobox.currentIndex()
        self.roi_plot_widget.select_roi(
            mca_num=mca_num, roi_num=roi_num, is_selected=is_selected
        )

    def mca_selected(self, is_selected: bool, mca_num: int = 0):
        """Handler for when an MCA row is selected for editing.

        Parameters
        ==========
        is_selected
          Will be true if the MCA row was selected, or false if the
          MCA row was deselected.

        """
        # Save the selected MCA number for later
        if is_selected:
            self._selected_mca = mca_num
        else:
            self._selected_mca = None
        # Set global controls for this MCA
        self.ui.mca_copyall_button.setEnabled(is_selected)
        # Disable the other rows
        mca_idx = mca_num
        for idx, disp in enumerate(self.mca_displays):
            if is_selected and idx != mca_idx:
                disp.setEnabled(False)
            else:
                disp.setEnabled(True)
        # Show this spectrum highlighted in the plots
        roi_num = self.ui.roi_combobox.currentIndex()
        self.mca_plot_widget.select_spectrum(
            mca_num=mca_num, roi_num=roi_num, is_selected=is_selected
        )

    def draw_roi_widgets(self, mca_idx):
        mca_num = mca_idx
        with self.disable_ui():
            # Update the plot widget with the new MCA number
            self.roi_plot_widget.target_mca = mca_num
            # Prepare all the ROI widgets
            layout = self.ui.rois_layout
            self.remove_widgets_from_layout(layout)
            self.roi_displays = []
            for roi_num in range(self.device.num_rois):
                disp = ROIEmbeddedDisplay(parent=self)
                disp.macros = json.dumps(
                    {
                        "DEV": self.device.name,
                        "MCA": mca_num,
                        "ROI": roi_num,
                        "NUM": roi_num,
                    }
                )
                disp.filename = "xrf_roi.py"
                # Respond when this ROI is selected
                disp.selected.connect(partial(self.roi_selected, roi_num=roi_num))
                disp.hovered.connect(
                    partial(self.roi_row_hovered.emit, mca_num, roi_num)
                )
                # Add the Embedded Display to the ROI Layout
                layout.addWidget(disp)
                self.roi_displays.append(disp)
            # Reset the selected ROI
            self.roi_selected(is_selected=False)
            # Make the global enable checkbox tri-state again
            self.ui.roi_enableall_checkbox.setCheckState(Qt.PartiallyChecked)

    def draw_mca_widgets(self, roi_idx):
        """Prepare a row for each element in the detector."""
        with self.disable_ui():
            # Prepare all the ROI widgets
            layout = self.ui.mcas_layout
            self.remove_widgets_from_layout(layout)
            self.mca_displays = []
            for mca_num in range(self.device.num_elements):
                disp = ROIEmbeddedDisplay(parent=self)
                disp.macros = json.dumps(
                    {
                        "DEV": self.device.name,
                        "MCA": mca_num,
                        "ROI": roi_idx,
                        "NUM": mca_num,
                    }
                )
                disp.filename = "xrf_roi.py"
                # Respond when this MCA is interacted with
                disp.selected.connect(partial(self.mca_selected, mca_num=mca_num))
                disp.hovered.connect(
                    partial(self.mca_row_hovered.emit, mca_num, roi_idx)
                )
                # Add the Embedded Display to the ROI Layout
                layout.addWidget(disp)
                self.mca_displays.append(disp)
            # Reset the selected MCA
            self.mca_selected(is_selected=False)
            # Make the global enable checkbox tri-state again
            self.ui.mca_enableall_checkbox.setCheckState(Qt.PartiallyChecked)

    def remove_widgets_from_layout(self, layout):
        # Delete existing ROI widgets
        for idx in reversed(range(layout.count())):
            layout.takeAt(idx).widget().deleteLater()


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
