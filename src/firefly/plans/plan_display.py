import asyncio
import logging
from dataclasses import dataclass
from typing import Sequence, Any

from bluesky_queueserver_api import BPlan
from ophyd_async.core import Device
from qasync import asyncSlot
from qtpy.QtWidgets import QWidget, QLineEdit, QComboBox, QTextEdit, QGridLayout, QPushButton, QSpinBox
from qtpy.QtCore import QObject, Signal

from firefly import display
from firefly.queue_button import QueueButton

log = logging.getLogger()


class PlanStubDisplay(display.FireflyDisplay):
    """Base class containing common functionality for basic plan stub window displays.
    Should be subclassed to produce a usable display.
    """

    plan_type: str
    scan_time_changed = Signal(float)
    total_time_changed = Signal(float)

    # Common widgets
    run_button: QueueButton

    def customize_ui(self):
        self.run_button = QueueButton(self)
        self.run_button.clicked.connect(self.queue_plan)

    async def _get_time(self, detector):
        """Get the dwell time value for a given detector."""
        time_signal = detector.default_time_signal
        if hasattr(time_signal, "get_value"):
            return await time_signal.get_value()
        return time_signal.get()

    def update_total_time(self):
        raise NotImplementedError

    def scan_durations(self, detector_time: float) -> tuple[float, float]:
        """Calculate the time needed for a single scan, and all scans.

        Placeholder for time calculation logic. Should be implemented
        in subclasses.


        Parameters
        ==========
        detector_time
          The time, in seconds, needed at each point for the
          detectors.

        Returns
        =======
        time_per_scan
          The time, in seconds, for each individual scan.
        total_time
          The time, in seconds, for all repeats of a scan.

        """
        raise NotImplementedError

    def plan_args(self):
        raise NotImplementedError

    def queue_plan(self, *args, **kwargs) -> BPlan:
        """Execute this plan on the queueserver."""
        args, kwargs = self.plan_args()
        # Build the queue item
        item = BPlan(self.plan_type, *args, **kwargs)
        # Submit the item to the queueserver
        log.info(f"Adding {self.plan_type} plan to queue: {item}.")
        for i in range(self.scan_repetitions):
            self.queue_item_submitted.emit(item)
        return item


class PlanDisplay(PlanStubDisplay):
    """Base class containing common features for basic plan displays.

    Should be subclassed to produce a usable display.

    """
    scan_repetitions: int = 1

    def plan_metadata(self) -> dict[str, Any]:
        """Build a metadata dictionary to be suitable for including in the plan."""
        return self.metadata_widget.metadata()


# -----------------------------------------------------------------------------
# :author:    Juanjuan Huang, Mark Wolfman
# :email:     juanjuan.huang@anl.gov, wolfman@anl.gov
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
