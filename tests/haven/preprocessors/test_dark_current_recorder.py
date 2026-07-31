import time

import pytest
from bluesky import plans as bp
from ophyd_async.core import soft_signal_rw

from haven.devices import SRS570PreAmplifier as SR570PreAmplifier
from haven.preprocessors import DarkCurrentRecorder


@pytest.mark.asyncio
async def test_records_with_no_history():
    detector = soft_signal_rw(int)
    await detector.connect(mock=True)
    preamp = SR570PreAmplifier("", name="preamp")
    await preamp.connect(mock=True)
    recorder = DarkCurrentRecorder(detectors=[detector], preamps=[preamp])
    msgs = list(recorder(bp.count([detector])))
    open_run_messages = [msg for msg in msgs if msg.command == "open_run"]
    assert len(open_run_messages) == 2
    dark_msg, plan_msg = open_run_messages
    assert dark_msg.kwargs["plan_name"] == "record_dark_current"
    assert plan_msg.kwargs["plan_name"] == "count"


preamp_readings = {
    "preamp-sensitivity_value": 0,
    "preamp-sensitivity_unit": 0,
    "preamp-offset_value": 0,
    "preamp-offset_unit": 0,
    "preamp-offset_on": 0,
    "preamp-offset_sign": 0,
    "preamp-invert": 0,
}


@pytest.mark.asyncio
async def test_skips_if_recent():
    """If dark current has been recorded recently, skip the measurement."""
    detector = soft_signal_rw(int)
    await detector.connect(mock=True)
    preamp = SR570PreAmplifier("", name="preamp")
    await preamp.connect(mock=True)
    ttl = 600
    last_time = time.monotonic() - ttl + 10
    recorder = DarkCurrentRecorder(
        detectors=[detector],
        preamps=[preamp],
        time_to_live=ttl,
        _last_measured=last_time,
        _preamp_readings=preamp_readings,
    )
    msgs = list(recorder(bp.count([detector])))
    open_run_messages = [msg for msg in msgs if msg.command == "open_run"]
    assert len(open_run_messages) == 1
    (plan_msg,) = open_run_messages
    assert plan_msg.kwargs["plan_name"] == "count"
    # Make sure the new time gets recorded
    assert recorder._last_measured == last_time


@pytest.mark.asyncio
async def test_records_if_old():
    detector = soft_signal_rw(int)
    await detector.connect(mock=True)
    preamp = SR570PreAmplifier("", name="preamp")
    await preamp.connect(mock=True)
    ttl = 600
    last_time = time.monotonic() - ttl - 10
    recorder = DarkCurrentRecorder(
        detectors=[detector],
        preamps=[preamp],
        time_to_live=ttl,
        _last_measured=last_time,
        _preamp_readings={"preamp": 0},
    )
    msgs = list(recorder(bp.count([detector])))
    open_run_messages = [msg for msg in msgs if msg.command == "open_run"]
    assert len(open_run_messages) == 2
    dark_msg, plan_msg = open_run_messages
    assert dark_msg.kwargs["plan_name"] == "record_dark_current"
    assert plan_msg.kwargs["plan_name"] == "count"


@pytest.mark.asyncio
async def test_records_if_preamps_changed():
    detector = soft_signal_rw(int)
    await detector.connect(mock=True)
    preamp = SR570PreAmplifier("", name="preamp")
    await preamp.connect(mock=True)
    ttl = 600
    last_time = time.monotonic() - ttl + 10
    recorder = DarkCurrentRecorder(
        detectors=[detector],
        preamps=[preamp],
        time_to_live=ttl,
        _last_measured=last_time,
        _preamp_readings=preamp_readings,
    )
    # Pretend the preamp gain changed and make sure the new dark current was recorded
    plan = recorder(bp.count([detector]))
    msgs = [
        next(plan),
        plan.send({"readback": 15}),  # rd() to check if changed
        *plan,
    ]
    open_run_messages = [msg for msg in msgs if msg.command == "open_run"]
    assert len(open_run_messages) == 2
    dark_msg, plan_msg = open_run_messages
    assert dark_msg.kwargs["plan_name"] == "record_dark_current"
    assert plan_msg.kwargs["plan_name"] == "count"


@pytest.mark.xfail
@pytest.mark.asyncio
async def test_adds_dark_current_uid():
    """Check that the run-dark_current UID gets added to the base plan metadata."""
    detector = soft_signal_rw(int)
    await detector.connect(mock=True)
    preamp = SR570PreAmplifier("", name="preamp")
    await preamp.connect(mock=True)
    recorder = DarkCurrentRecorder(
        detectors=[detector],
        preamps=[preamp],
    )
    # Pretend the preamp gain changed and make sure the new dark current was recorded
    plan = recorder(bp.count([detector]))
    msgs = [*plan]
    from pprint import pprint

    pprint(msgs)
    assert False


@pytest.mark.xfail
@pytest.mark.asyncio
async def test_stashes_preamp_readings():
    detector = soft_signal_rw(int)
    await detector.connect(mock=True)
    preamp = SR570PreAmplifier("", name="preamp")
    await preamp.connect(mock=True)
    recorder = DarkCurrentRecorder(
        detectors=[detector],
        preamps=[preamp],
    )
    # Pretend the preamp gain changed and make sure the new dark current was recorded
    plan = recorder(bp.count([detector]))
    msgs = [*plan]
    from pprint import pprint

    pprint(msgs)
    assert False


@pytest.mark.xfail
@pytest.mark.asyncio
async def test_stashes_last_recorded_time():
    detector = soft_signal_rw(int)
    await detector.connect(mock=True)
    preamp = SR570PreAmplifier("", name="preamp")
    await preamp.connect(mock=True)
    recorder = DarkCurrentRecorder(
        detectors=[detector],
        preamps=[preamp],
    )
    # Pretend the preamp gain changed and make sure the new dark current was recorded
    plan = recorder(bp.count([detector]))
    msgs = [*plan]
    from pprint import pprint

    pprint(msgs)
    assert False


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2026, UChicago Argonne, LLC
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
