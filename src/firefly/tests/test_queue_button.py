from firefly.queue_button import Colors, QueueButton


def test_queue_button_style(qtbot):
    """Does the queue button change color/icon based on the queue state."""
    btn = QueueButton()
    qtbot.addWidget(btn)
    # Initial style should be disabled and plain
    assert not btn.isEnabled()
    assert btn.styleSheet() == ""
    # State when queue server is open and idle (no autostart)
    queue_state = {
        "worker_environment_exists": True,
        "items_in_queue": 0,
        "re_state": "idle",
        "queue_autostart_enabled": False,
    }
    btn.update_queue_style(queue_state)
    assert btn.isEnabled()
    assert Colors.ADD_TO_QUEUE in btn.styleSheet()
    assert btn.text() == "Add to Queue"
    # State when queue server is open and idle (w/ autostart)
    queue_state = {
        "worker_environment_exists": True,
        "items_in_queue": 0,
        "re_state": "idle",
        "queue_autostart_enabled": True,
    }
    btn.update_queue_style(queue_state)
    assert btn.isEnabled()
    assert Colors.RUN_QUEUE in btn.styleSheet()
    assert btn.text() == "Run"
    # State when queue server is open and idle
    queue_state = {
        "worker_environment_exists": True,
        "items_in_queue": 0,
        "re_state": "running",
        "queue_autostart_enabled": True,
    }
    btn.update_queue_style(queue_state)
    assert btn.isEnabled()
    assert Colors.ADD_TO_QUEUE in btn.styleSheet()
    assert btn.text() == "Add to Queue"


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
