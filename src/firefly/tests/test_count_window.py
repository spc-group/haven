from unittest import mock

from bluesky_queueserver_api import BPlan
from qtpy import QtCore

from firefly.plans.count import CountDisplay


def test_count_plan_queued(qtbot, sim_registry, monkeypatch):
    display = CountDisplay()
    qtbot.addWidget(display)
    monkeypatch.setattr(display, "submit_queue_item", mock.MagicMock())
    display.ui.num_spinbox.setValue(5)
    display.ui.delay_spinbox.setValue(0.5)
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", "I0"]
    )
    expected_item = BPlan("count", num=5, detectors=["vortex_me4", "I0"], delay=0.5)
    # Run the code under test
    display.queue_plan()
    # Test submitted item is correct
    assert display.submit_queue_item.called
    submitted_item = display.submit_queue_item.call_args[0][0]
    assert submitted_item.to_dict() == expected_item.to_dict()

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
