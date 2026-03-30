import pytest
from bluesky import RunEngine
from bluesky import plan_stubs as bps
from ophyd_async.core import soft_signal_rw

from haven.preprocessors import aps_suspenders_wrapper
from haven.preprocessors.aps_suspenders import SuspendFloor, SuspendWhenChanged


def test_storage_ring_current_suspender(aps):
    # Simulate a valid read on the APS status
    wrapped = aps_suspenders_wrapper(bps.null(), aps)
    msgs = list(wrapped)
    assert msgs[0].command == "read"
    assert msgs[0].obj is aps.machine_status
    # Get the rest of the messages
    assert msgs[1].command == "install_suspender"
    assert msgs[2].command == "install_suspender"
    assert msgs[3].command == "null"
    assert msgs[4].command == "remove_suspender"
    assert msgs[5].command == "remove_suspender"


def test_not_user_mode(aps):
    # Simulate a valid read on the APS status
    wrapped = aps_suspenders_wrapper(bps.null(), aps)
    msg = next(wrapped)
    assert msg.command == "read"
    assert msg.obj is aps.machine_status
    # Check that we only read the machine status and run the internal plan
    status_reading = {"aps.machine_status.name": {"value": "MAINTENANCE"}}
    msgs = [msg, wrapped.send(status_reading), *wrapped]
    assert msgs[1].command == "null"
    assert len(msgs) == 2


def test_open_shutters(aps, shutters):
    shutter = shutters[0]
    plan = aps_suspenders_wrapper(bps.null(), aps=aps, shutters=[shutter])
    msgs = list(plan)
    permit_suspender = msgs[1].args[0]
    open_shutters_plan = permit_suspender._post_plan
    shutter_msgs = list(open_shutters_plan())
    assert shutter_msgs[0].command == "set"
    assert shutter_msgs[0].obj is shutter
    assert shutter_msgs[0].args[0] == 0


@pytest.mark.asyncio
async def test_suspend_when_changed_installation():
    RE = RunEngine({})
    signal = soft_signal_rw(float)
    await signal.connect(mock=True)
    suspender = SuspendWhenChanged(
        signal=signal,
        expected_value="PERMIT",
        allow_resume=True,
    )
    suspender.install(RE)
    suspender.remove()


@pytest.mark.asyncio
async def test_suspend_when_changed_call():
    # Prepare an ophyd signal
    BAD, GOOD = (1, 2)
    signal = soft_signal_rw(float, name="signal", initial_value=GOOD)
    await signal.connect(mock=True)
    # Prepare the suspender
    suspender = SuspendWhenChanged(
        signal=signal,
        expected_value=GOOD,
        allow_resume=True,
    )
    RE = RunEngine({})
    suspender.install(RE)
    # Use the suspender
    try:
        assert suspender.expected_value == GOOD
        assert not suspender._tripped
        suspender({"signal": {"value": BAD}})
        assert suspender._tripped
        suspender({"signal": {"value": GOOD}})
        assert not suspender._tripped
    finally:
        suspender.remove()


@pytest.mark.asyncio
async def test_suspend_floor_installation():
    RE = RunEngine({})
    signal = soft_signal_rw(float, initial_value=0)
    await signal.connect(mock=True)
    suspender = SuspendFloor(
        signal=signal,
        suspend_thresh=1,
    )
    suspender.install(RE)
    suspender.remove()


@pytest.mark.asyncio
async def test_suspend_floor_call():
    # Prepare an ophyd signal
    BAD, THRESH, GOOD = (1, 2, 3)
    signal = soft_signal_rw(float, name="signal", initial_value=GOOD)
    await signal.connect(mock=True)
    # Prepare the suspender
    suspender = SuspendFloor(
        signal=signal,
        suspend_thresh=THRESH,
    )
    RE = RunEngine({})
    suspender.install(RE)
    # Use the suspender
    try:
        assert not suspender._tripped
        suspender({"signal": {"value": BAD}})
        assert suspender._tripped
        suspender({"signal": {"value": GOOD}})
        assert not suspender._tripped
    finally:
        suspender.remove()


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2025, UChicago Argonne, LLC
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
