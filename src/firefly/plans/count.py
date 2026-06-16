import logging

from bluesky_queueserver_api import BPlan
from qasync import asyncSlot

from firefly.plans import display

log = logging.getLogger()


class CountDisplay(display.PlanDisplay):

    async def update_devices(self, registry):
        """Set available components in the device list."""
        await super().update_devices(registry)
        await self.detectors_list.update_devices(registry)

    def customize_ui(self):
        super().customize_ui()
        # Connect signals for total time updates
        self.ui.num_events_spinbox.valueChanged.connect(self.update_total_time)
        self.ui.livetime_spinbox.valueChanged.connect(self.update_total_time)
        self.ui.collections_per_event_spinbox.valueChanged.connect(
            self.update_total_time
        )
        self.ui.delay_spinbox.valueChanged.connect(self.update_total_time)
        self.ui.spinBox_repeat_scan_num.valueChanged.connect(self.update_total_time)
        # Default metadata values

    @asyncSlot()
    async def update_total_time(self):
        livetime = self.ui.livetime_spinbox.value()
        num_readings = self.ui.num_events_spinbox.value()
        delay = self.ui.delay_spinbox.value()
        coll_per_event = self.ui.collections_per_event_spinbox.value()
        scan_livetime = livetime * num_readings * coll_per_event
        scan_delay = delay * (num_readings - 1)
        time_per_scan = scan_livetime + scan_delay
        efficiency = scan_livetime / time_per_scan if time_per_scan != 0 else None
        self.ui.scan_duration_label.set_seconds(time_per_scan, efficiency=efficiency)
        repetitions = self.ui.spinBox_repeat_scan_num.value()
        total_time = time_per_scan * repetitions
        self.ui.total_duration_label.set_seconds(total_time, efficiency=efficiency)

    def plan(self):
        args = ()
        names = [det.name for det in self.ui.detectors_list.selected_detectors()]
        kwargs = {
            "detectors": names,
            "num": self.ui.num_events_spinbox.value(),
            "delay": self.ui.delay_spinbox.value(),
            "livetime": self.ui.livetime_spinbox.value(),
            "md": self.plan_metadata(),
            "collections_per_event": self.ui.collections_per_event_spinbox.value(),
        }
        return BPlan("count", *args, **kwargs)

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        item = self.plan()
        # Submit the item to the queueserver
        log.info("Add ``count()`` plan to queue.")
        log.debug(item)

        # repeat scans
        for i in range(self.ui.spinBox_repeat_scan_num.value()):
            self.queue_item_submitted.emit(item)

    def ui_filename(self):
        return "plans/count.ui"


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
