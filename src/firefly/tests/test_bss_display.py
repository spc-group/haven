import datetime as dt
from zoneinfo import ZoneInfo

chicago_tz = ZoneInfo("America/Chicago")

import pytest
import time_machine
from qtpy.QtCore import QDateTime, Qt
from qtpy.QtGui import QStandardItemModel

from firefly.bss import BssDisplay
from haven.bss import Esaf, Proposal, User


@pytest.fixture()
def bss_api(mocker):
    api = mocker.AsyncMock()
    api.esafs.return_value = [
        Esaf(
            esaf_id="5555555",
            description="Doing X-ray science with X-rays",
            status="Pending",
            title="X-ray Science!",
            start=dt.datetime(2025, 5, 25, 12, 15, 39),
            end=dt.datetime(2025, 5, 26, 12, 15, 39),
            users=[
                User(
                    badge="0000001",
                    first_name="Rosalind",
                    last_name="Franklin",
                    email="",
                    is_pi=True,
                    institution=None,
                ),
                User(
                    badge="0000002",
                    first_name="Francis",
                    last_name="Crick",
                    email="",
                    is_pi=False,
                    institution=None,
                ),
            ],
            sector="25",
        )
    ]

    api.proposals.return_value = [
        Proposal(
            title="X-ray science!",
            proposal_id="8675309",
            users=[
                User(
                    badge="0000003",
                    first_name="Daria",
                    last_name="Morgendorffer",
                    email="",
                    is_pi=True,
                    institution="",
                ),
                User(
                    badge="0000004",
                    first_name="Quinn",
                    last_name="Morgendorffer",
                    email="",
                    is_pi=False,
                    institution="",
                ),
            ],
            start=dt.datetime(2025, 5, 25, 12, 29, 0),
            end=dt.datetime(2025, 5, 25, 13, 29, 0),
            duration=dt.timedelta(seconds=3600),
            mail_in=False,
            proprietary=False,
        )
    ]
    yield api


@pytest.fixture()
def display(qtbot, bss_api):
    display = BssDisplay(api=bss_api)
    qtbot.addWidget(display)
    # display.cycle_lineedit.setText("2025-1")
    # display.beamline_lineedit.setText("255-ID-Z")
    return display


async def test_beamline_cycle_defaults(display):
    # These values are set by the iconfig_testing.toml file
    assert display.beamline_lineedit.text() == "255-ID-Z"
    assert display.cycle_lineedit.text() == "2025-1"


async def test_bss_proposal_model(display, bss_api):
    display.ui.beamline_lineedit.setText("255-ID-Z")
    display.ui.cycle_lineedit.setText("3024-1")
    await display.load_models()
    # Check model construction
    assert isinstance(display.proposal_model, QStandardItemModel)
    bss_api.proposals.assert_called_once_with(cycle="3024-1", beamline="255-ID-Z")
    assert display.proposal_model.rowCount() == 1
    # Check that the view has the model attached
    assert display.ui.proposal_view.model() is display.proposal_model


async def test_bss_proposal_updating(display, qtbot):
    await display.load_models()
    # Set some base-line values for hitting the API
    display.ui.proposal_id_lineedit.setText("")
    # Change the proposal item
    item = display.proposal_model.item(0, 1)
    assert item is not None
    rect = display.proposal_view.visualRect(item.index())
    # See if the proposal PVs were updated
    with qtbot.waitSignal(display.proposal_selected):
        qtbot.mouseClick(
            display.proposal_view.viewport(), Qt.LeftButton, pos=rect.center()
        )
    assert display.ui.update_proposal_button.isEnabled()
    id_text = display.ui.proposal_id_lineedit.text()
    assert id_text != "8675309"
    # Now update the PROPOSAL details
    display.update_proposal()
    id_text = display.ui.proposal_id_lineedit.text()
    assert id_text == "8675309"
    assert display.ui.proposal_title_lineedit.text() == "X-ray science!"
    assert (
        display.ui.proposal_start_datetimeedit.dateTime().toPyDateTime()
        == dt.datetime(2025, 5, 25, 12, 29, 0)
    )
    assert (
        display.ui.proposal_end_datetimeedit.dateTime().toPyDateTime()
        == dt.datetime(2025, 5, 25, 13, 29, 0)
    )
    assert (
        display.ui.proposal_users_lineedit.text()
        == "Daria Morgendorffer, Quinn Morgendorffer"
    )
    assert display.ui.proposal_pis_lineedit.text() == "Daria Morgendorffer"


async def test_bss_proposals(display):
    proposals = await display.proposals()
    proposal = proposals[0]
    assert proposal.title == "X-ray science!"
    assert proposal.proposal_id == "8675309"
    assert len(proposal.users) == 2
    assert proposal.start == dt.datetime(2025, 5, 25, 12, 29, 0)
    assert proposal.end == dt.datetime(2025, 5, 25, 13, 29, 0)


async def test_bss_esaf_model(display, bss_api):
    display.ui.beamline_lineedit.setText("255-ID-Z")
    display.ui.cycle_lineedit.setText("3024-1")
    await display.load_models()
    # Check model construction
    assert isinstance(display.esaf_model, QStandardItemModel)
    bss_api.esafs.assert_called_once_with(year="3024", sector="255")
    assert display.esaf_model.rowCount() == 1
    # Check that the view has the model attached
    assert display.ui.esaf_view.model() is display.esaf_model


async def test_bss_esaf_updating(display, qtbot):
    await display.load_models()
    # Set some base-line values on the IOC
    display.ui.esaf_id_lineedit.setText("")
    # Change the ESAF item
    item = display.esaf_model.item(0, 1)
    assert item is not None
    rect = display.esaf_view.visualRect(item.index())
    # Clicking a list entry should enable the update button
    with qtbot.waitSignal(display.esaf_selected):
        qtbot.mouseClick(display.esaf_view.viewport(), Qt.LeftButton, pos=rect.center())
    assert display.ui.update_esaf_button.isEnabled()
    id_text = display.ui.esaf_id_lineedit.text()
    assert id_text != "5555555"
    # Now update the ESAF details
    display.update_esaf()
    id_text = display.ui.esaf_id_lineedit.text()
    assert id_text == "5555555"
    assert display.ui.esaf_status_label.text() == "Pending"
    assert display.ui.esaf_title_lineedit.text() == "X-ray Science!"
    assert display.ui.esaf_start_datetimeedit.dateTime().toPyDateTime() == dt.datetime(
        2025, 5, 25, 12, 15, 39
    )
    assert display.ui.esaf_end_datetimeedit.dateTime().toPyDateTime() == dt.datetime(
        2025, 5, 26, 12, 15, 39
    )
    assert display.ui.esaf_users_lineedit.text() == "Rosalind Franklin, Francis Crick"
    assert display.ui.esaf_pis_lineedit.text() == "Rosalind Franklin"


async def test_bss_esafs(display):
    # Check values
    esafs = await display.esafs()
    esaf = esafs[0]
    assert esaf.description == "Doing X-ray science with X-rays"
    assert esaf.title == "X-ray Science!"
    assert esaf.esaf_id == "5555555"
    assert len(esaf.users) == 2
    assert esaf.start == dt.datetime(2025, 5, 25, 12, 15, 39)
    assert esaf.end == dt.datetime(2025, 5, 26, 12, 15, 39)


@time_machine.travel(dt.datetime(2025, 5, 28, 15, 51, tzinfo=chicago_tz))
def test_bss_metadata(display, bss_api, qtbot):
    """Checks the properties of the model that gets emitted when the
    widgets are changed.

    """
    display.esaf_id_lineedit.setText("1225467")
    display.esaf_status_label.setText("Rejected!")
    esaf_start = dt.datetime(2025, 5, 26, 12, 33, 13)
    esaf_end = dt.datetime(2025, 5, 26, 13, 47, 13)
    display.esaf_start_datetimeedit.setDateTime(
        QDateTime.fromSecsSinceEpoch(int(esaf_start.timestamp()))
    )
    display.esaf_end_datetimeedit.setDateTime(
        QDateTime.fromSecsSinceEpoch(int(esaf_end.timestamp()))
    )
    display.esaf_users_lineedit.setText("Freddy Mercury, Brian May")
    display.esaf_pis_lineedit.setText("Freddy Mercury")
    display.proposal_title_lineedit.setText("MAMAAAAAAA")
    display.proposal_id_lineedit.setText("9876543")
    proposal_start = dt.datetime(2025, 5, 28, 12, 33, 13)
    proposal_end = dt.datetime(2025, 5, 29, 15, 47, 13)
    display.proposal_start_datetimeedit.setDateTime(
        QDateTime.fromSecsSinceEpoch(int(proposal_start.timestamp()))
    )
    display.proposal_end_datetimeedit.setDateTime(
        QDateTime.fromSecsSinceEpoch(int(proposal_end.timestamp()))
    )
    display.proposal_users_lineedit.setText("Animal, Zoot")
    display.proposal_pis_lineedit.setText("Animal")
    display.proposal_mailin_checkbox.setChecked(True)
    display.proposal_proprietary_checkbox.setChecked(False)
    # Run the handler and see if the model gets emitted
    with qtbot.waitSignal(display.metadata_changed, timeout=1000) as blocker:
        display.esaf_title_lineedit.setText("Spam and eggs science")
        # display.check_metadata()
    # Check that the metadata matches
    assert blocker.args[0] == {
        "esaf_title": "Spam and eggs science",
        "esaf_status": "Rejected!",
        "esaf_id": "1225467",
        "esaf_start": "2025-05-26T12:33:13-05:00",
        "esaf_end": "2025-05-26T13:47:13-05:00",
        "esaf_users": "Freddy Mercury, Brian May",
        "esaf_PIs": "Freddy Mercury",
        "proposal_title": "MAMAAAAAAA",
        "proposal_id": "9876543",
        "proposal_start": "2025-05-28T12:33:13-05:00",
        "proposal_end": "2025-05-29T15:47:13-05:00",
        "proposal_users": "Animal, Zoot",
        "proposal_PIs": "Animal",
        "proposal_is_mail_in": True,
        "proposal_is_proprietary": False,
    }


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
