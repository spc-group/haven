import logging

from bluesky_queueserver_api import BPlan

from firefly import display

log = logging.getLogger()


class CountDisplay(display.FireflyDisplay):

    async def update_devices(self, registry):
        """Set available components in the device list."""
        await super().update_devices(registry)
        await self.ui.detectors_list.update_devices(registry)

    def customize_ui(self):
        self.ui.run_button.clicked.connect(self.queue_plan)

    def queue_plan(self, *args, **kwargs):
        """Execute this plan on the queueserver."""
        # Get scan parameters from widgets
        num_readings = self.ui.num_spinbox.value()
        delay = self.ui.delay_spinbox.value()
        detectors = self.ui.detectors_list.selected_detectors()
        # Build the queue item

        item = BPlan("count", delay=delay, num=num_readings, detectors=detectors)
        # Submit the item to the queueserver
        log.info("Add ``count()`` plan to queue.")
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
