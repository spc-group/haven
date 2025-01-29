"""A QPushButton that responds to the state of the queue server."""

import logging

import qtawesome as qta
from qtpy import QtGui, QtWidgets
from strenum import StrEnum

log = logging.getLogger(__name__)


class Colors(StrEnum):
    ADD_TO_QUEUE = "rgb(0, 123, 255)"
    RUN_QUEUE = "rgb(25, 135, 84)"


class QueueButton(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initially disable the button until the status of the queue can be determined
        self.setDisabled(True)

    def update_queue_style(self, status: dict):
        if status.get("worker_environment_exists", False):
            self.setEnabled(True)
        else:
            # Should be disabled because the queue is closed
            self.setDisabled(True)
        # Coloration for the whether the item would get run immediately
        if status["re_state"] == "idle" and status["queue_autostart_enabled"]:
            # Will play immediately
            self.setStyleSheet(
                f"background-color: {Colors.RUN_QUEUE};\n"
                f"border-color: {Colors.RUN_QUEUE};"
            )
            self.setIcon(qta.icon("fa5s.play"))
            if self.text() in ["Run", "Add to Queue", ""]:
                self.setText("Run")
            self.setToolTip("Add this plan to the queue and start it immediately.")
        elif status["worker_environment_exists"]:
            # Will be added to the queue
            self.setStyleSheet(
                f"background-color: {Colors.ADD_TO_QUEUE};\n"
                f"border-color: {Colors.ADD_TO_QUEUE};\n"
            )
            self.setIcon(qta.icon("fa5s.list"))
            if self.text() in ["Run", "Add to Queue", ""]:
                self.setText("Add to Queue")
            self.setToolTip("Add this plan to the queue to run later.")
        else:
            # Regular old (probably disabled) button
            self.setStyleSheet("")
            self.setIcon(QtGui.QIcon())


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
