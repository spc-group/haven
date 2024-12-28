import asyncio

import numpy as np
import pandas as pd
import pytest
from pyqtgraph import PlotItem

from firefly.xrf_detector import XRFDetectorDisplay

# detectors = ["dxp", "xspress"]
detectors = ["xspress"]


@pytest.fixture()
def xrf_display(request, qtbot):
    """Parameterized fixture for creating a display based on a specific
    detector class.

    """
    # Figure out which detector we're using
    det = request.getfixturevalue(request.param)
    # Create the display
    display = XRFDetectorDisplay(macros={"DEV": det.name})
    qtbot.addWidget(display)
    # Set sensible starting values
    spectra = np.random.default_rng(seed=0).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    plot_widget = display.mca_plot_widget
    energies = np.arange(1024)
    plot_widget.update_spectrum(0, pd.Series(spectra[0], index=energies))
    plot_widget.update_spectrum(1, pd.Series(spectra[1], index=energies))
    plot_widget.update_spectrum(2, pd.Series(spectra[2], index=energies))
    plot_widget.update_spectrum(3, pd.Series(spectra[3], index=energies))
    yield display


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_device_name(xrf_display):
    label = xrf_display.ui.detector_name_label
    assert label.text() == xrf_display.device.name


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_mca_count_labels_created(xrf_display):
    """Check that QLabel objs are created for each element."""
    layout = xrf_display.ui.mcas_layout
    assert layout.rowCount() == 6  # 4 elements plus heading and total
    assert layout.itemAtPosition(1, 0).widget().text() == "Total"
    assert layout.itemAtPosition(5, 1).widget() is xrf_display._count_labels[3]


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
async def test_update_mca_spectra(xrf_display, qtbot):
    spectra = np.random.default_rng(seed=0).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    mca_plot_widget = xrf_display.ui.mca_plot_widget
    # Check that a PlotItem was created in the fixture
    plot_item = mca_plot_widget.ui.plot_widget.getPlotItem()
    assert isinstance(plot_item, PlotItem)
    # Clear the data items so we can test them later
    plot_item.clear()
    # plot_widget.update_spectrum(spectrum=spectra[0], mca_idx=1)
    with qtbot.waitSignal(mca_plot_widget.plot_changed):
        xrf_display._spectrum_channels[0].value_slot(spectra[0])
        xrf_display._spectrum_channels[1].value_slot(spectra[1])
        await asyncio.sleep(0.1)
    # Check that the spectrum was plotted
    data_items = plot_item.listDataItems()
    assert len(data_items) == 2
    energies = np.linspace(5, 10235, num=1024)
    np.testing.assert_equal(data_items[0].xData, energies)
    # Check that previous plots get cleared
    spectra2 = np.random.default_rng(seed=1).integers(
        0, 65536, dtype=np.int_, size=(4, 1024)
    )
    with qtbot.waitSignal(mca_plot_widget.plot_changed):
        xrf_display._spectrum_channels[0].value_slot(spectra2[0])
        await asyncio.sleep(0.1)
    data_items = plot_item.listDataItems()
    assert len(data_items) == 2


@pytest.mark.xfail()
@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_mca_hovering(xrf_display):
    """Is the spectrum highlighted when the element row is selected."""
    # Check that the region is hidden at startup
    plot_widget = xrf_display.mca_plot_widget
    # Now highlight a spectrum, and confirm it is visible
    plot_widget.highlight_spectrum(mca_num=2, roi_num=0, hovered=True)
    # assert region.brush.color().name() == "#ff7f0e"
    # Unhighlight and confirm it is invisible
    plot_widget.highlight_spectrum(mca_num=1, roi_num=0, hovered=False)


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_update_spectral_widgets(xrf_display):
    spectrum = np.ones(shape=(100,), dtype=int) * 10
    xrf_display.update_spectral_widgets(mca_num=0, spectrum=spectrum, spectra=[])
    mcas_layout = xrf_display.ui.mcas_layout
    elem0_label = mcas_layout.itemAtPosition(2, 1).widget()
    assert elem0_label.text() == "1_000"
    total_label = mcas_layout.itemAtPosition(1, 1).widget()
    assert total_label.text() == "0"
    # Add a second spectrum for a separate element
    xrf_display.update_spectral_widgets(
        mca_num=1, spectrum=spectrum * 2, spectra=[spectrum, spectrum * 2]
    )
    elem1_label = mcas_layout.itemAtPosition(3, 1).widget()
    assert elem1_label.text() == "2_000"
    total_label = mcas_layout.itemAtPosition(1, 1).widget()
    assert total_label.text() == "3_000"


@pytest.mark.parametrize("xrf_display", detectors, indirect=True)
def test_detector_state_style(xrf_display):
    """The label should change color, etc depending on detector state."""
    # Check initial state
    lbl = xrf_display.ui.detector_state_label
    assert "rgb(" not in lbl.styleSheet()
    assert "bold" not in lbl.styleSheet()
    # Update state and check again
    xrf_display.update_state_style("Acquire")
    assert "rgb(" in lbl.styleSheet()
    assert "bold" in lbl.styleSheet()


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
