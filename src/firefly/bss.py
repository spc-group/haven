import asyncio
import logging
import re

import qtawesome as qta
from qasync import asyncSlot
from qtpy.QtCore import QDateTime, Qt, Signal
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QAbstractItemView, QDateTimeEdit

from firefly import display
from haven import load_config
from haven.bss import BssApi, Esaf, Proposal

log = logging.getLogger(__name__)


class BssDisplay(display.FireflyDisplay):
    """A PyDM display for the beamline scheduling system (BSS)."""

    _proposal_col_names = [
        "proposal_id",
        "title",
        "start",
        "end",
        "users",
        "mail_in",
        "proprietary",
    ]
    _esaf_col_names = ["esaf_id", "title", "start", "end", "users", "status"]
    # Signals
    metadata_changed = Signal(dict)
    # These are only used for testing, maybe they can be removed in future releases
    _proposal_selected = Signal()
    _esaf_selected = Signal()

    def __init__(self, api=None, args=None, macros={}, **kwargs):
        if api is None:
            api = BssApi()
        self.api = api
        super().__init__(args=args, macros=macros, **kwargs)

    def customize_ui(self):
        super().customize_ui()
        icon = qta.icon("fa6s.arrow-right")
        self.ui.update_proposal_button.setIcon(icon)
        self.ui.update_proposal_button.clicked.connect(self.update_proposal)
        self.ui.update_esaf_button.setIcon(icon)
        self.ui.update_esaf_button.clicked.connect(self.update_esaf)
        self.load_bss_button.clicked.connect(self.load_models)
        self.beamline_lineedit.returnPressed.connect(self.load_models)
        self.cycle_lineedit.returnPressed.connect(self.load_models)
        self.load_bss_button.setIcon(qta.icon("fa6s.table-list"))
        # Want tables to select the whole row
        self.ui.proposal_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.proposal_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.esaf_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.esaf_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Emit new metadata when the widgets are changed
        self.ui.esaf_title_lineedit.textChanged.connect(self.check_metadata)
        self.ui.esaf_id_lineedit.textChanged.connect(self.check_metadata)
        self.ui.esaf_start_datetimeedit.dateTimeChanged.connect(self.check_metadata)
        self.ui.esaf_end_datetimeedit.dateTimeChanged.connect(self.check_metadata)
        self.ui.esaf_pis_lineedit.textChanged.connect(self.check_metadata)
        self.ui.esaf_users_lineedit.textChanged.connect(self.check_metadata)
        self.ui.proposal_title_lineedit.textChanged.connect(self.check_metadata)
        self.ui.proposal_id_lineedit.textChanged.connect(self.check_metadata)
        self.ui.proposal_start_datetimeedit.dateTimeChanged.connect(self.check_metadata)
        self.ui.proposal_end_datetimeedit.dateTimeChanged.connect(self.check_metadata)
        self.ui.proposal_pis_lineedit.textChanged.connect(self.check_metadata)
        self.ui.proposal_users_lineedit.textChanged.connect(self.check_metadata)
        self.ui.proposal_mailin_checkbox.stateChanged.connect(self.check_metadata)
        self.ui.proposal_proprietary_checkbox.stateChanged.connect(self.check_metadata)
        # Set defaults in widgets
        bss_config = load_config()["bss"]
        self.beamline_lineedit.setText(bss_config.get("beamline", ""))
        self.cycle_lineedit.setText(bss_config.get("cycle", ""))

    def check_metadata(self):
        """Emit the latest metadata from display widgets.

        Emits
        =====
        bss_metadata_changed
          The latest metadata as entered into the widgets.

        """
        md = self.metadata()
        self.metadata_changed.emit(md)

    def metadata(self) -> dict[str, str]:
        """Read the UI widgets and prepare a metadata dictionary."""

        def dt_iso(widget: QDateTimeEdit) -> str:
            pydt = widget.dateTime().toPyDateTime()
            return pydt.astimezone().isoformat()

        return {
            "esaf_title": self.ui.esaf_title_lineedit.text(),
            "esaf_id": self.ui.esaf_id_lineedit.text(),
            "esaf_status": self.ui.esaf_status_label.text(),
            "esaf_start": dt_iso(self.ui.esaf_start_datetimeedit),
            "esaf_end": dt_iso(self.ui.esaf_end_datetimeedit),
            "esaf_PIs": self.ui.esaf_pis_lineedit.text(),
            "esaf_users": self.ui.esaf_users_lineedit.text(),
            "proposal_title": self.ui.proposal_title_lineedit.text(),
            "proposal_id": self.ui.proposal_id_lineedit.text(),
            "proposal_start": dt_iso(self.ui.proposal_start_datetimeedit),
            "proposal_end": dt_iso(self.ui.proposal_end_datetimeedit),
            "proposal_PIs": self.ui.proposal_pis_lineedit.text(),
            "proposal_users": self.ui.proposal_users_lineedit.text(),
            "proposal_is_mail_in": self.ui.proposal_mailin_checkbox.isChecked(),
            "proposal_is_proprietary": self.ui.proposal_proprietary_checkbox.isChecked(),
        }

    async def proposals(self) -> list[Proposal]:
        beamline = self.ui.beamline_lineedit.text()
        cycle = self.ui.cycle_lineedit.text()
        # Get proposal data from the API
        if "" in [beamline, cycle]:
            log.info(f"Skipping proposal lookup for {cycle=}, {beamline=}")
            return []
        proposals = await self.api.proposals(cycle=cycle, beamline=beamline)
        # Parse the API payload into the format for the BSS IOC
        return proposals

    async def esafs(self) -> list[Esaf]:
        beamline = self.ui.beamline_lineedit.text()
        cycle = self.ui.cycle_lineedit.text()
        # Parse the arguments
        try:
            sector, *_ = beamline.split("-")
        except ValueError:
            log.info(f"Skipping ESAF lookup for {beamline=}")
            return []
        match = re.match(r"^(\d{4})[-/]\d{1,2}", cycle)
        if not match:
            log.info(f"Skipping ESAF lookup for {cycle=}")
            return []
        (year,) = match.groups()
        esafs = await self.api.esafs(year=year, sector=sector)
        return esafs

    @asyncSlot()
    async def load_models(self):
        # Load data
        proposals, esafs = await asyncio.gather(self.proposals(), self.esafs())
        # Create proposal model object
        col_names = self._proposal_col_names
        self.proposal_model = QStandardItemModel()
        self.proposal_model.setHorizontalHeaderLabels(col_names)
        # Load individual proposals
        log.info(f"Loaded {len(proposals)} proposals and {len(esafs)} ESAFs.")
        for proposal in proposals:
            items = [QStandardItem(str(getattr(proposal, col))) for col in col_names]
            for item in items:
                item.setData(proposal, role=Qt.UserRole)
            self.proposal_model.appendRow(items)
        self.ui.proposal_view.setModel(self.proposal_model)
        # Create proposal model object
        col_names = self._esaf_col_names
        self.esaf_model = QStandardItemModel()
        self.esaf_model.setHorizontalHeaderLabels(col_names)
        # Load individual esafs
        for esaf in esafs:
            items = [QStandardItem(str(getattr(esaf, col))) for col in col_names]
            for item in items:
                item.setData(esaf, role=Qt.UserRole)
            self.esaf_model.appendRow(items)
        self.ui.esaf_view.setModel(self.esaf_model)
        # Connect slots for when proposal/ESAF is changed
        self.ui.proposal_view.selectionModel().currentChanged.connect(
            self.select_proposal
        )
        self.ui.esaf_view.selectionModel().currentChanged.connect(self.select_esaf)

    def select_proposal(self, current, previous):
        # Enable controls for updating the metadata
        self.ui.update_proposal_button.setEnabled(True)
        self._proposal_selected.emit()

    def update_proposal(self):
        """Set the metadata widgets based on which proposal is selected."""
        # Determine which proposal was selected
        index = self.ui.proposal_view.currentIndex()
        proposal = index.model().itemFromIndex(index).data(role=Qt.UserRole)
        # Change the proposal widgets
        self.ui.proposal_id_lineedit.setText(proposal.proposal_id)
        self.ui.proposal_title_lineedit.setText(proposal.title)
        qstart = QDateTime.fromMSecsSinceEpoch(int(proposal.start.timestamp() * 1000))
        qend = QDateTime.fromMSecsSinceEpoch(int(proposal.end.timestamp() * 1000))
        self.ui.proposal_start_datetimeedit.setDateTime(qstart)
        self.ui.proposal_end_datetimeedit.setDateTime(qend)
        # Convert user info into commma-separated lists
        users_text = ", ".join(
            [f"{user.first_name} {user.last_name}" for user in proposal.users]
        )
        self.ui.proposal_users_lineedit.setText(users_text)
        pis = [user for user in proposal.users if user.is_pi]
        pis_text = ", ".join([f"{pi.first_name} {pi.last_name}" for pi in pis])
        self.ui.proposal_pis_lineedit.setText(pis_text)

    def select_esaf(self, current, previous):
        # Enable controls for updating the metadata
        self.ui.update_esaf_button.setEnabled(True)
        self._esaf_selected.emit()

    def update_esaf(self):
        """Set the metadata widgets based on which ESAF is selected."""
        # Determine which esaf was selected
        index = self.ui.esaf_view.currentIndex()
        esaf = index.model().itemFromIndex(index).data(role=Qt.UserRole)
        # Change the ESAF widgets
        self.ui.esaf_id_lineedit.setText(esaf.esaf_id)
        self.ui.esaf_status_label.setText(esaf.status)
        self.ui.esaf_title_lineedit.setText(esaf.title)
        qstart = QDateTime.fromMSecsSinceEpoch(int(esaf.start.timestamp() * 1000))
        qend = QDateTime.fromMSecsSinceEpoch(int(esaf.end.timestamp() * 1000))
        self.ui.esaf_start_datetimeedit.setDateTime(qstart)
        self.ui.esaf_end_datetimeedit.setDateTime(qend)
        # Convert user info into commma-separated lists
        users_text = ", ".join(
            [f"{user.first_name} {user.last_name}" for user in esaf.users]
        )
        self.ui.esaf_users_lineedit.setText(users_text)
        pis = [user for user in esaf.users if user.is_pi]
        pis_text = ", ".join([f"{pi.first_name} {pi.last_name}" for pi in pis])
        self.ui.esaf_pis_lineedit.setText(pis_text)

    def ui_filename(self):
        return "bss.ui"


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
