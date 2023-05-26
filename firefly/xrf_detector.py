import logging
import subprocess
from pathlib import Path
from typing import Sequence, Optional
import json
from contextlib import contextmanager
from functools import partial
from collections import defaultdict
import gc

from qtpy import uic
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QWidget
import qtawesome as qta
import pyqtgraph
import pydm
from pydm.widgets import PyDMEmbeddedDisplay, PyDMChannel
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import TABLEAU_COLORS

import haven
from firefly import display, FireflyApplication

import sys

np.set_printoptions(threshold=sys.maxsize)


log = logging.getLogger(__name__)


pyqtgraph.setConfigOption("imageAxisOrder", "row-major")

colors = list(TABLEAU_COLORS.values())


class ROIRegion(pyqtgraph.LinearRegionItem):
    mca_num: int
    roi_num: int

    lo_channel: PyDMChannel
    hi_channel: PyDMChannel

    region_upper_changed = Signal(int)
    region_lower_changed = Signal(int)

    _last_upper: int = None
    _last_lower: int = None

    def __init__(self, address: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.address = address
        # Set up channels to the IOC
        self.hi_channel = PyDMChannel(
            address=f"{address}.hi_chan._write_pv",
            value_slot=self.set_region_upper,
            value_signal=self.region_upper_changed
        )
        self.hi_channel.connect()
        self.lo_channel = PyDMChannel(
            address=f"{address}.lo_chan._write_pv",
            value_slot=self.set_region_lower,
            value_signal=self.region_lower_changed
        )
        self.lo_channel.connect()
        self.sigRegionChangeFinished.connect(self.handle_region_change)
        # Set initial display state
        self.setVisible(False)

    def handle_region_change(self):
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
        log.debug(f"Setting new region lower bound: {new_lower}")
        old_region = self.getRegion()
        new_region = (new_lower, old_region[1])
        if new_region != old_region:
            self.setRegion(new_region)
        self._last_lower = new_lower
    
    def set_region_upper(self, new_upper):
        """Set the upper value of the highlighted region."""
        log.debug(f"Setting new region upper bound: {new_upper}")
        old_region = self.getRegion()
        new_region = (old_region[0], new_upper)
        if new_region != old_region:
            self.setRegion(new_region)
        self._last_upper = new_upper
   


class XRFPlotWidget(QWidget):
    ui_dir = Path(__file__).parent
    _data_items: defaultdict
    _selected_spectrum: int = None
    _region_items: dict
    device_name: str = ""

    # Signals
    plot_changed = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_items = defaultdict(lambda: None)
        # self._lo_channels = {}
        # self._hi_channels = {}
        # self._lo_signals = {}
        # self._hi_signals = {}
        self._region_items = {}
        self.ui = uic.loadUi(self.ui_dir / "xrf_plot.ui", self)
        # Create plotting items
        self.plot_item = self.ui.plot_widget.addPlot(row=0, col=0)
        self.plot_item.addLegend()
        # self.ui.region.sigRegionChangeFinished.connect(self.handle_region_change)

    # def new_region(self, idx):
    #     """Create a new pyqtgraph region for selecting ROI range."""
    #     new_region = pyqtgraph.LinearRegionItem()
    #     new_region.setVisible(False)
    #     color = self.mca_color(idx)
    #     new_region.setBrush(f"{color}10")
    #     new_region.setHoverBrush(f"{color}20")
    #     for line in new_region.lines:
    #         line.setPen(f"{color}50")
    #     self.plot_item.addItem(new_region)
    #     return new_region

    def region(self, mca_num, roi_num):
        key = (mca_num, roi_num)
        # Create a new region item if necessary
        if key not in self._region_items.keys():
            address = f"oph://{self.device_name}.mcas.mca{mca_num}.rois.roi{roi_num}"
            color = self.mca_color(mca_num)
            region = ROIRegion(address=address,
                               brush=f"{color}10",
                               hoverBrush=f"{color}20",
                               pen=f"{color}50",)
            self.plot_item.addItem(region)
            self._region_items[key] = region
            # self.hi_channel(mca_num=mca_num, roi_num=roi_num)
            # self.lo_channel(mca_num=mca_num, roi_num=roi_num)
            # changed_slot = partial(self.handle_region_change,
            #                        mca_num=mca_num, roi_num=roi_num, region=region)
            # region.sigRegionChangeFinished.connect(changed_slot)
        # Return the region item
        return self._region_items[key]

    # def hi_signal(self, mca_num, roi_num):
    #     key = (mca_num, roi_num)
    #     # Create a new signal
    #     if key not in self._hi_signals.keys():
    #         self._hi_signals[key] = Signal(int)
    #     # Return the signal
    #     return self._hi_signals[key]

    # def lo_signal(self, mca_num, roi_num):
    #     key = (mca_num, roi_num)
    #     # Create a new signal
    #     if key not in self._lo_signals.keys():
    #         self._lo_signals[key] = Signal(int)
    #     # Return the signal
    #     return self._lo_signals[key]
    
    # def hi_channel(self, mca_num, roi_num):
    #     key = (mca_num, roi_num)
    #     # Create a new hi channel if necessary
    #     if key not in self._hi_channels.keys():
    #         address = f"oph://{self.device_name}.mcas.mca{mca_num}.rois.roi{roi_num}.hi_chan._write_pv"
    #         new_chan = pydm.PyDMChannel(
    #             address=address,
    #             value_slot=partial(self.set_region_upper, mca_num=mca_num, roi_num=roi_num),
    #             value_signal=self.hi_signal(mca_num=mca_num, roi_num=roi_num),
    #         )
    #         new_chan.connect()
    #         self._hi_channels[key] = new_chan
    #     return self._hi_channels[key]

    # def lo_channel(self, mca_num, roi_num):
    #     key = (mca_num, roi_num)
    #     # Create a new hi channel if necessary
    #     if key not in self._lo_channels.keys():
    #         address = f"oph://{self.device_name}.mcas.mca{mca_num}.rois.roi{roi_num}.lo_chan._write_pv"
    #         new_chan = pydm.PyDMChannel(
    #             address=address,
    #             value_slot=partial(self.set_region_lower, mca_num=mca_num, roi_num=roi_num),
    #             value_signal=self.lo_signal(mca_num=mca_num, roi_num=roi_num),
    #         )
    #         new_chan.connect()
    #         self._lo_channels[key] = new_chan
    #     return self._lo_channels[key]
    
    def handle_region_change(self, mca_num, roi_num, region):
        lower, upper = region.getRegion()
        lower = round(lower)
        upper = round(upper)
        self.lo_signal(mca_num=mca_num, roi_num=roi_num).emit(lower)
        self.hi_signal(mca_num=mca_num, roi_num=roi_num).emit(upper)

    # def set_region_lower(self, new_lower: int, mca_num: int, roi_num: int):
    #     log.debug(f"Setting new region lower bound: {new_lower}")
    #     region = self.region(mca_num=mca_num, roi_num=roi_num)
    #     upper = region.getRegion()[1]
    #     region.setRegion((new_lower, upper))

    def update_spectrum(self, mca_num, spectrum):
        """Plot the spectrum associated with the given MCA index."""
        # Create the plot item itself if necessary
        log.debug(f"New spectrum ({mca_num}): {repr(spectrum)}")
        row, col = (0, 0)
        plot_item = self.ui.plot_widget.getItem(row=row, col=col)
        # Get rid of the previous plots
        if (existing_item := self._data_items[mca_num]) is not None:
            plot_item.removeItem(existing_item)
        # Plot the spectrum
        xdata = np.arange(len(spectrum))
        color = self.mca_color(mca_num)
        self._data_items[mca_num] = plot_item.plot(
            xdata, spectrum, name=mca_num, pen=color
        )
        # Add region markers
        self.plot_changed.emit()

    def mca_color(self, mca_num):
        return colors[(mca_num - 1) % len(colors)]

    def select_spectrum(self, mca_num, roi_num, is_selected):
        """Select an active spectrum to modify."""
        log.debug(f"Selecting spectrum {mca_num}")
        self._selected_spectrum = mca_num if is_selected else None
        self.highlight_spectrum(mca_num=mca_num, roi_num=roi_num, hovered=is_selected)

    def highlight_spectrum(self, mca_num, roi_num, hovered):
        """Highlight a spectrum and lowlight the rest.

        *mca_num* is the number (1-indexed) of the spectrum plotted.

        If *hovered* is true, then set the highlights, otherwise clear
        them.

        """
        # Get the actual line plot
        solid, semisolid, transparent = (1.0, 0.55, 0.15)
        for key, data_item in self._data_items.items():
            if hovered:
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
                    f"Reverting to previously selected spectrum: {self._selected_spectrum}"
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
            self.show_region(show=True, mca_num=self._selected_spectrum, roi_num=roi_num)
        else:
            self.show_region(show=False, mca_num=mca_num, roi_num=roi_num)

    def show_region(self, show: bool, mca_num: int = 1, roi_num: int=0):
        # Hide all the other regions
        for (mca, roi), region in self._region_items.items():
            region.setVisible(False)
        # Show/hide the specific region requested
        self.region(mca_num=mca_num, roi_num=roi_num).setVisible(show)


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
    roi_displays: Sequence = []
    mca_displays: Sequence = []
    _spectrum_channels: Sequence
    _selected_mca: int = None
    _mca_lower_receiver = None
    _mca_upper_receiver = None

    # Signals
    spectrum_changed = Signal(int, object)  # (MCA index, spectrum)
    mca_row_hovered = Signal(int, int, bool)  # (MCA num, roi_num, entered)

    # # PyDM Channels
    # mca_hi_channel: FireflyChannel = None
    # mca_lo_channel: FireflyChannel = None

    def ui_filename(self):
        return "xrf_detector.ui"

    def customize_ui(self):
        device = self.device
        self.ui.mca_plot_widget.device_name = self.device.name
        # Set ROI and element selection comboboxes
        self.ui.mca_combobox.currentIndexChanged.connect(self.draw_roi_widgets)
        self.ui.roi_combobox.currentIndexChanged.connect(self.draw_mca_widgets)
        elements = [str(i) for i in range(1, device.num_elements + 1)]
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
        self.ui.acquire_button.setIcon(qta.icon("fa5s.play"))
        # Buttons for modifying all ROI settings
        self.ui.mca_copyall_button.setIcon(qta.icon("fa5.clone"))
        self.ui.mca_copyall_button.clicked.connect(self.copy_selected_mca)
        self.ui.mca_enableall_checkbox.setCheckState(Qt.PartiallyChecked)
        # Connect signals for when spectra change
        self.spectrum_changed.connect(self.ui.roi_plot_widget.update_spectrum)
        self.spectrum_changed.connect(self.ui.mca_plot_widget.update_spectrum)
        self.mca_row_hovered.connect(self.ui.mca_plot_widget.highlight_spectrum)

    def copy_selected_mca(self):
        """Copy the label, hi channel, and lo channel values from the selected
        MCA row to all other visible MCA rows.

        """
        log.debug(f"Copying MCA {self._selected_mca}")
        # Get existing values from selected MCA row
        mca_idx = self._selected_mca - 1
        source_display = self.mca_displays[mca_idx]
        new_label = source_display.embedded_widget.ui.label_lineedit.text()
        new_lower = source_display.embedded_widget.ui.lower_lineedit.text()
        new_upper = source_display.embedded_widget.ui.upper_lineedit.text()
        widget = source_display.embedded_widget.ui.upper_lineedit
        # Set all the other MCA rows with values from selected MCA row
        for idx, display in enumerate(self.mca_displays):
            if idx != mca_idx:
                display.embedded_widget.ui.label_lineedit.setText(new_label)
                display.embedded_widget.ui.lower_lineedit.setText(new_lower)
                display.embedded_widget.ui.upper_lineedit.setText(new_upper)
                # Send the new value over the wire
                for widget in [display.embedded_widget.ui.label_lineedit,
                               display.embedded_widget.ui.lower_lineedit,
                               display.embedded_widget.ui.upper_lineedit]:
                    if widget._connected:
                        widget.send_value()

    def handle_new_spectrum(self, new_spectrum, mca_num):
        self.spectrum_changed.emit(mca_num, new_spectrum)

    def customize_device(self):
        # Load the device from the registry
        device_name = self.macros()["DEV"]
        self.device = device = haven.registry.find(device_name)
        # Set up data channels
        self._spectrum_channels = []
        for mca_num in range(1, self.device.num_elements + 1):
            address = f"oph://{device.name}.mcas.mca{mca_num}.spectrum"
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
        FireflyApplication.instance().processEvents()
        yield
        # Re-enabled everything
        widget.setEnabled(True)
        widget.setCursor(old_cursor)

    def roi_selected(self, is_selected: bool, roi_idx=None):
        """Handler for when an ROI is selected for editing.

        Parameters
        ==========
        is_selected
          Will be true if the ROI was selected, or false if the ROI
          was deselected.

        """
        for idx, disp in enumerate(self.roi_displays):
            if is_selected and idx != roi_idx:
                disp.setEnabled(False)
            else:
                disp.setEnabled(True)

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
        mca_idx = mca_num - 1
        for idx, disp in enumerate(self.mca_displays):
            if is_selected and idx != mca_idx:
                disp.setEnabled(False)
            else:
                disp.setEnabled(True)
        # Show this spectrum highlighted in the plots
        roi_num = self.ui.roi_combobox.currentIndex()
        self.mca_plot_widget.select_spectrum(mca_num=mca_num, roi_num=roi_num,
                                             is_selected=is_selected)

    # def setup_mca_channels(self, mca_num: int, connect: bool):
    #     """Connect the PVs for changing the ROI selection region on the plot.

    #     Parameters
    #     ==========
    #     mca_num
    #       The 1-index number for this MCA.
    #     connect
    #       Whether to connect (``True``) or disconnect (``False``) the
    #       channels.

    #     """
    #     # Disconnect old PV channels
    #     old_channels = [self.mca_hi_channel, self.mca_lo_channel]
    #     log.debug(f"Disconnecting previous MCA channels: {old_channels}")
    #     for channel in old_channels:
    #         if channel is not None:
    #             channel.disconnect()
    #             channel = None
    #     # gc.collect()
    #     # Set a new addresses
    #     roi_num = self.ui.roi_combobox.currentIndex()
    #     # oph://${DEV}.mcas.mca${MCA}.rois.roi${ROI}.lo_chan._write_pv
    #     if connect:
    #         mca_cpt = getattr(self.device.mcas, f"mca{mca_num}")
    #     elif self._selected_mca is not None:
    #         # Connect the previously selected MCA bounds
    #         mca_cpt = getattr(self.device.mcas, f"mca{self._selected_mca}")
    #         # Kludge to make sure the colors are right
    #         self.mca_plot_widget.show_region(show=True, mca_num=self._selected_mca)
    #     else:
    #         mca_cpt = None
    #     # Create and connect the channels
    #     try:
    #         roi = getattr(mca_cpt.rois, f"roi{roi_num}")
    #         hi_address = f"ca://{roi.hi_chan.pvname}"
    #         lo_address = f"ca://{roi.lo_chan.pvname}"
    #     except AttributeError:
    #         log.warning(f"Cannot find hi/lo channels for {mca_cpt}")
    #         roi = None
    #         hi_address = f"oph://{getattr(mca_cpt, 'name', 'unknown')}.rois.roi{roi_num}.hi_chan._write_pv"
    #         lo_address = f"oph://{getattr(mca_cpt, 'name', 'unknown')}.rois.roi{roi_num}.lo_chan"
    #     log.debug(f"Creating new channels: {lo_address}, {hi_address}")
    #     self.mca_hi_channel = FireflyChannel(
    #         address=hi_address,
    #         value_slot=self.mca_plot_widget.set_region_upper,
    #         value_signal=self.mca_plot_widget.region_upper_changed,
    #     )
    #     self.mca_hi_channel.connect()
    #     self.mca_lo_channel = FireflyChannel(
    #         address=lo_address,
    #         value_slot=self.mca_plot_widget.set_region_lower,
    #         value_signal=self.mca_plot_widget.region_lower_changed,
    #     )
    #     self.mca_lo_channel.connect()

    def draw_roi_widgets(self, element_idx):
        with self.disable_ui():
            # Prepare all the ROI widgets
            layout = self.ui.rois_layout
            self.remove_widgets_from_layout(layout)
            self.roi_displays = []
            for roi_idx in range(self.device.num_rois):
                disp = ROIEmbeddedDisplay(parent=self)
                disp.macros = json.dumps(
                    {
                        "DEV": self.device.name,
                        "MCA": element_idx + 1,
                        "ROI": roi_idx,
                        "NUM": roi_idx,
                    }
                )
                disp.filename = "xrf_roi.py"
                # Respond when this ROI is selected
                disp.selected.connect(partial(self.roi_selected, roi_idx=roi_idx))
                # Add the Embedded Display to the ROI Layout
                layout.addWidget(disp)
                self.roi_displays.append(disp)

    def draw_mca_widgets(self, roi_idx):
        """Prepare a row for each element in the detector."""
        with self.disable_ui():
            # Prepare all the ROI widgets
            layout = self.ui.mcas_layout
            self.remove_widgets_from_layout(layout)
            self.mca_displays = []
            for mca_num in range(1, self.device.num_elements + 1):
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
                disp.hovered.connect(partial(self.mca_row_hovered.emit, mca_num, roi_idx))
                # Add the Embedded Display to the ROI Layout
                layout.addWidget(disp)
                self.mca_displays.append(disp)
            # Reset the selected MCA
            self.mca_selected(is_selected=False)

    def remove_widgets_from_layout(self, layout):
        # Delete existing ROI widgets
        for idx in reversed(range(layout.count())):
            layout.takeAt(idx).widget().deleteLater()
