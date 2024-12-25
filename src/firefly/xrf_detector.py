import json
import logging
import sys
from collections import defaultdict
from itertools import product
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
from qtpy.QtWidgets import QApplication, QWidget, QLabel

from firefly import display
from haven import beamline

np.set_printoptions(threshold=sys.maxsize)


log = logging.getLogger(__name__)


pyqtgraph.setConfigOption("imageAxisOrder", "row-major")

colors = list(TABLEAU_COLORS.values())


class AcquireStates(IntEnum):
    DONE = 0
    ACQUIRING = 1


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

    _spectrum_channels: Sequence
    _selected_mca: int = None
    _mca_lower_receiver = None
    _mca_upper_receiver = None

    _spectra: dict

    num_header_rows = 2

    # Signals
    mca_row_hovered = Signal(int, int, bool)  # (MCA num, roi_num, entered)

    def ui_filename(self):
        return "xrf_detector.ui"

    def customize_ui(self):
        self._spectra = {}
        device = self.device
        self.setWindowTitle(device.name)
        self.ui.mca_plot_widget.device_name = self.device.name
        # Create count totals for each element
        self.draw_mca_widgets()
        # Button for starting/stopping the detector
        self.ui.oneshot_button.setIcon(qta.icon("fa5s.camera"))
        super().customize_ui()

    def launch_caqtdm(
        self,
    ):
        super().launch_caqtdm(macros={"P": self.device.prefix.strip(":")})

    def handle_new_spectrum(self, new_spectrum, mca_num):
        self._spectra[mca_num] = new_spectrum
        self.ui.mca_plot_widget.update_spectrum(mca_num=mca_num, spectrum=new_spectrum)
        self.update_spectral_widgets(mca_num=mca_num, spectrum=new_spectrum, spectra=self._spectra.values())

    def update_spectral_widgets(self, mca_num: int, spectrum: Sequence, spectra: Sequence[np.ndarray]):
        """Update the values of labels with totals, etc from the spectra."""
        row = mca_num + self.num_header_rows
        count_label = self.ui.mcas_layout.itemAtPosition(row, 1).widget()
        count_label.setText(f"{np.sum(spectrum):_}")
        # Update the sum-total widget
        total = 0
        total_label = self.ui.mcas_layout.itemAtPosition(1, 1).widget()
        for spec in spectra:
            total += np.sum(spec)
        total_label.setText(f"{total:_}")
    
    def customize_device(self):
        # Load the device from the registry
        device_name = self.macros()["DEV"]
        self.device = beamline.devices[device_name]
        # Set up data channels
        self._spectrum_channels = []
        for element_num, element in self.device.elements.items():
            address = f"haven://{element.name}.spectrum"
            channel = pydm.PyDMChannel(
                address=address,
                value_slot=partial(self.handle_new_spectrum, mca_num=element_num),
            )
            channel.connect()
            self._spectrum_channels.append(channel)

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

    def draw_mca_widgets(self):
        """Prepare a row for each element in the detector."""
        # Prepare all the ROI widgets
        layout = self.ui.mcas_layout
        self.clear_elements_layout(layout)
        self._count_labels = {}
        for idx, (key, mca) in enumerate(self.device.elements.items()):
            row = idx + self.num_header_rows
            # Label for the number of the MCA's detector element
            key_label = QLabel()
            key_label.setText(str(key))
            layout.addWidget(key_label, row, 0)
            # Label for the counts for this element
            count_label = QLabel()
            count_label.setText("##########")
            layout.addWidget(count_label, row, 1)
            self._count_labels[key] = count_label

    def clear_elements_layout(self, layout):
        rows = range(self.num_header_rows, layout.rowCount())
        cols = range(layout.columnCount())
        for row, col in product(rows, cols):
            item = layout.itemAtPosition(row, col)
            layout.removeItem(item)
            item.widget().deleteLater()


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
