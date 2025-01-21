import logging
import sys
from collections import defaultdict
from contextlib import contextmanager
from enum import Enum, IntEnum
from functools import partial
from itertools import product
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import pydm
import pyqtgraph
import qtawesome as qta
from matplotlib.colors import TABLEAU_COLORS
from qasync import asyncSlot
from qtpy import uic
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QApplication, QLabel, QWidget

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
        plot_item.getAxis("bottom").setLabel("Energy", units="eV")
        super().__init__(parent=parent, background=background, plotItem=plot_item)


class XRFPlotWidget(QWidget):
    """The outer widget, containing the plot and related controls."""

    ui_dir = Path(__file__).parent
    _data_items: defaultdict
    _selected_spectrum: int | None = None
    device_name: str = ""
    target_mca: int = None

    # Signals
    plot_changed = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_items = defaultdict(lambda: None)
        self.ui = uic.loadUi(self.ui_dir / "xrf_plot.ui", self)
        # Create plotting items
        plot_item = self.ui.plot_widget.getPlotItem()
        plot_item.addLegend()
        plot_item.hover_coords_changed.connect(self.ui.coords_label.setText)

    def update_spectrum(self, mca_num: int, spectrum: pd.Series):
        """Plot the spectrum associated with the given MCA index.

        Parameters
        ==========
        mca_num
          The 0-index for this MCA. E.g. the 2nd element would have
          *mca_num* of ``1``.
        spectrum
          The spectrum to plot.
        """
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
            xdata = spectrum.index
            color = self.spectrum_color(mca_num)
            self._data_items[mca_num] = plot_item.plot(
                xdata, spectrum.values, name=mca_num, pen=color
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


class Color(str, Enum):
    """Taken from bootstrap 5 alert components."""

    BLUE = "rgb(5, 81, 96)"
    GREY = "rgb(226, 227, 229)"
    GREEN = "rgb(10, 54, 34)"
    RED = "rgb(248, 215, 218)"
    YELLOW = "rgb(255, 243, 205)"


class XRFDetectorDisplay(display.FireflyDisplay):

    _spectrum_channels: Sequence
    _spectra: dict
    num_header_rows: int = 2

    # For styling the detector state attribute
    state_styles = {
        "Acquire": f"color: {Color.GREEN}; font-weight: bold;",
        "Saving": f"color: {Color.GREEN}",
        "Error": f"color: {Color.RED}; font-weight: bold;",
        "Disconnected": f"color: {Color.RED}",
        "Aborting": f"color: {Color.YELLOW}",
        "Initializing": f"color: {Color.YELLOW}",
        "Waiting": f"color: {Color.YELLOW}",
    }

    def ui_filename(self):
        return "xrf_detector.ui"

    def customize_ui(self):
        self._spectra = {}
        device = self.device
        self.setWindowTitle(device.name)
        self.ui.mca_plot_widget.device_name = self.device.name
        # Label for the device_name
        self.ui.detector_name_label.setText(device.name)
        # Create count totals for each element
        self.draw_mca_widgets()
        # Button for starting/stopping the detector
        self.ui.acquire_button.setIcon(qta.icon("fa5s.camera"))
        # Handler for updating the detector state label style
        self.det_state_channel = pydm.PyDMChannel(
            address=self.ui.detector_state_label.channel,
            value_slot=self.update_state_style,
        )
        self.det_state_channel.connect()
        super().customize_ui()

    def update_state_style(self, new_state: str):
        new_style = self.state_styles.get(new_state, "")
        self.ui.detector_state_label.setStyleSheet(new_style)

    @asyncSlot(object)
    async def handle_new_spectrum(self, new_spectrum, mca_num):
        # Calclulate energies for this spectrum
        ev_per_bin = await self.device.ev_per_bin.get_value()
        energies = (np.arange(new_spectrum.shape[0]) + 0.5) * ev_per_bin
        spectrum = pd.Series(new_spectrum, index=energies)
        self._spectra[mca_num] = spectrum
        # Update UI widgets
        self.ui.mca_plot_widget.update_spectrum(mca_num=mca_num, spectrum=spectrum)
        self.update_spectral_widgets(
            mca_num=mca_num, spectrum=spectrum, spectra=self._spectra.values()
        )

    def update_spectral_widgets(
        self, mca_num: int, spectrum: Sequence, spectra: Sequence[np.ndarray]
    ):
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
            # Label for the dead time for this element
            dt_signal = mca.dead_time_percent.name
            dt_label = pydm.widgets.PyDMLabel(init_channel=f"haven://{dt_signal}")
            layout.addWidget(dt_label, row, 2)

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
