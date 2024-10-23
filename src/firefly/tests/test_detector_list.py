import pytest
from qtpy.QtCore import Qt

from firefly.detector_list import DetectorListView


@pytest.fixture()
async def view(qtbot, sim_registry, dxp):
    view = DetectorListView()
    qtbot.addWidget(view)
    await view.update_devices(sim_registry)
    return view


def test_detector_model(view):
    assert hasattr(view, "detector_model")
    assert view.detector_model.item(0).text() == "vortex_me4"


def test_selected_detectors(qtbot, view):
    """Do we get the list of detectors after they have been selected?"""
    # No detectors selected, so empty list
    assert view.selected_detectors() == []
    # Select a detector and see if the selection updates
    item = view.detector_model.item(0)
    assert item is not None
    rect = view.visualRect(item.index())
    with qtbot.waitSignal(view.selectionModel().selectionChanged):
        qtbot.mouseClick(view.viewport(), Qt.LeftButton, pos=rect.center())
    assert view.selected_detectors() == ["vortex_me4"]


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
