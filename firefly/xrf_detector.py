import logging
import subprocess
from pathlib import Path
from typing import Sequence, Optional
import json
from contextlib import contextmanager
from functools import partial
from collections import defaultdict

from qtpy import uic
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QWidget
import qtawesome as qta
import pyqtgraph
import pydm
from pydm.widgets import PyDMEmbeddedDisplay
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


class XRFPlotWidget(QWidget):
    ui_dir = Path(__file__).parent
    _data_items: defaultdict

    # Signals
    plot_changed = Signal()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_items = defaultdict(lambda: None)
        self.ui = uic.loadUi(self.ui_dir / "xrf_plot.ui", self)

    def update_spectrum(self, mca_num, spectrum):
        """Plot the spectrum associated with the given MCA index."""
        # Create the plot item itself if necessary
        log.debug(f"New spectrum ({mca_num}): {repr(spectrum)}")
        row, col = (0, 0)
        if (plot_item := self.ui.plot_widget.getItem(row=row, col=col)) is None:
            plot_item = self.ui.plot_widget.addPlot(row=row, col=col)
        # Get ride of the previous plots
        if (existing_item := self._data_items[mca_num]) is not None:
            plot_item.removeItem(existing_item)
        # Plot the spectrum
        xdata = np.arange(len(spectrum))
        color = colors[(mca_num-1) % len(colors)]
        self._data_items[mca_num] = plot_item.plot(xdata, spectrum, label=mca_num, pen=color)
        self.plot_changed.emit()

    def highlight_spectrum(self, mca_num, hovered):
        """Highlight a spectrum and lowlight the rest.

        *mca_num* is the number (1-indexed) of the spectrum plotted.

        If *hovered* is true, then set the highlights, otherwise clear
        them.

        """
        # Get the actual line plot
        for key, data_item in self._data_items.items():
            is_dimmed = (key != mca_num) and hovered
            if is_dimmed:
                data_item.setOpacity(0.2)
            else:
                data_item.setOpacity(1.)


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
    
    # Signals
    spectrum_changed = Signal(int, object)  # (MCA index, spectrum)
    mca_row_hovered = Signal(int, bool)  # (MCA num, entered)

    def ui_filename(self):
        return "xrf_detector.ui"

    def customize_ui(self):
        device = self.device
        # Set ROI and element selection comboboxes
        self.ui.mca_combobox.currentIndexChanged.connect(self.draw_roi_widgets)
        self.ui.roi_combobox.currentIndexChanged.connect(self.draw_mca_widgets)
        elements = [str(i) for i in range(1, device.num_elements+1)]
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
        # Connect signals for when spectra change
        self.spectrum_changed.connect(self.ui.roi_plot_widget.update_spectrum)
        self.spectrum_changed.connect(self.ui.mca_plot_widget.update_spectrum)
        self.mca_row_hovered.connect(self.ui.mca_plot_widget.highlight_spectrum)

    def handle_new_spectrum(self, new_spectrum, mca_num):
        self.spectrum_changed.emit(mca_num, new_spectrum)

    def customize_device(self):
        # Load the device from the registry
        device_name = self.macros()["DEV"]
        self.device = device = haven.registry.find(device_name)
        # Set up data channels
        self._spectrum_channels = []
        for mca_num in range(1, self.device.num_elements+1):
            address = f"oph://{device.name}.mcas.mca{mca_num}.spectrum"
            channel = pydm.PyDMChannel(
                address=address,
                # value_slot=partial(self.spectrum_changed.emit, mca_num),
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

    def mca_selected(self, is_selected: bool, mca_idx=None):
        """Handler for when an MCA row is selected for editing.
        
        Parameters
        ==========
        is_selected
          Will be true if the MCA row was selected, or false if the
          MCA row was deselected.

        """
        for idx, disp in enumerate(self.mca_displays):
            if is_selected and idx != mca_idx:
                disp.setEnabled(False)
            else:
                disp.setEnabled(True)
                
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
                        "MCA": element_idx+1,
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
        """Prepare a row for each element in the detector.

        I.e. the "ROIs" tab

        """
        with self.disable_ui():
            # Prepare all the ROI widgets
            layout = self.ui.mcas_layout
            self.remove_widgets_from_layout(layout)
            self.mca_displays = []
            for mca_num in range(1, self.device.num_elements+1):
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
                disp.selected.connect(
                    partial(self.mca_selected, mca_idx=mca_num-1))
                disp.hovered.connect(
                    partial(self.mca_row_hovered.emit, mca_num))
                # Add the Embedded Display to the ROI Layout
                layout.addWidget(disp)
                self.mca_displays.append(disp)

    def remove_widgets_from_layout(self, layout):
        # Delete existing ROI widgets
        for idx in reversed(range(layout.count())):
            layout.takeAt(idx).widget().deleteLater()

