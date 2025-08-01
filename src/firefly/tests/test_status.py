import pytest
from pydm.widgets import PyDMByteIndicator
from qtpy.QtWidgets import QFormLayout

from firefly.status import StatusDisplay


@pytest.fixture()
def display(qtbot, shutters, xia_shutter, sim_registry):
    disp = StatusDisplay()
    qtbot.addWidget(disp)
    return disp


def test_shutter_controls(display):
    """Do shutter controls get added to the window?"""
    form = display.ui.beamline_layout
    # Check label text
    label0 = form.itemAt(4, QFormLayout.LabelRole)
    assert "shutter" in label0.widget().text().lower()
    # Check the widgets for the shutter
    layout0 = form.itemAt(4, QFormLayout.FieldRole)
    indicator = layout0.itemAt(0).widget()
    assert isinstance(indicator, PyDMByteIndicator)
    open_btn = layout0.itemAt(1).widget()
    assert open_btn.text() == "Open"
    close_btn = layout0.itemAt(2).widget()
    assert close_btn.text() == "Close"


def test_bss_widgets(display):
    display.update_bss_metadata(
        {
            "proposal_id": "1234567",
            "proposal_title": "Science!",
            "esaf_id": "987654",
            "esaf_title": "Science!",
            "esaf_status": "Approved",
            "esaf_end": "2025-05-29T17:53:00-05:00",
            "esaf_users": "Rosalind Franklin, James Crick",
        }
    )
    assert display.ui.proposal_id_label.text() == "1234567"
    assert display.ui.proposal_title_label.text() == "Science!"
    assert display.ui.esaf_id_label.text() == "987654"
    assert display.ui.esaf_title_label.text() == "Science!"
    assert display.ui.esaf_status_label.text() == "Approved"
    assert display.ui.esaf_end_date_label.text() == "2025-05-29T17:53:00-05:00"
    assert display.ui.esaf_users_label.text() == "Rosalind Franklin, James Crick"


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
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
