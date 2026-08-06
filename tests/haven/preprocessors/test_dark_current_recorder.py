import logging
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
    recorder = DarkCurrentRecorder(
        detectors=[detector], preamps=[preamp], _is_subscribed=True
    )
    msgs = list(recorder(bp.count([detector])))
    open_run_messages = [msg for msg in msgs if msg.command == "open_run"]
    assert len(open_run_messages) == 2
    dark_msg, plan_msg = open_run_messages
    assert dark_msg.kwargs["plan_name"] == "record_dark_current"
    assert plan_msg.kwargs["plan_name"] == "count"


@pytest.mark.asyncio
async def test_warns_if_not_subscribed():
    detector = soft_signal_rw(int)
    await detector.connect(mock=True)
    preamp = SR570PreAmplifier("", name="preamp")
    await preamp.connect(mock=True)
    recorder = DarkCurrentRecorder(
        detectors=[detector], preamps=[preamp], _is_subscribed=False
    )
    with pytest.warns(UserWarning):
        msgs = list(recorder(bp.count([detector])))


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
        _is_subscribed=True,
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
        _is_subscribed=True,
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
        _is_subscribed=True,
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
        _scan_uid="abc-123",
        _is_subscribed=True,
    )
    # Pretend the preamp gain changed and make sure the new dark current was recorded
    plan = recorder(bp.count([detector]))
    msgs = [*plan]
    dark_run_msg, scan_run_msg = [msg for msg in msgs if msg.command == "open_run"]
    # The first `record_dark_current()` run shouldn't reference another dark current run
    assert "dark_current_uid" not in dark_run_msg.kwargs
    # The actual scan metadata should reference another dark_current_run
    assert scan_run_msg.kwargs["dark_current_uid"] == "abc-123"


start_doc = {
    "uid": "7b8014c3-c9cd-4349-9e81-6255f7e1306d",
    "time": 1785643862.633221,
    "versions": {"ophyd": "1.11.1", "ophyd_async": "0.20.1", "bluesky": "1.14.6"},
    "scan_id": 2,
    "plan_type": "generator",
    "plan_name": "record_dark_current",
    "detectors": ["preamp"],
    "num_points": 1,
    "num_intervals": 0,
    "plan_args": {
        "detectors": [
            "<haven.devices.srs570.SRS570PreAmplifier object at 0x7f692c43dbe0>"
        ],
        "num": 1,
        "delay": 0.0,
    },
    "hints": {"dimensions": [(("time",), "primary")]},
}
descriptor_doc = {
    "configuration": {
        "preamp": {
            "data": {
                "preamp-gain": 1000000000000.0,
                "preamp-blank": False,
                "preamp-bias_value": 0,
                "preamp-offset_unit": "pA",
                "preamp-offset_on": False,
                "preamp-offset_cal": "CAL",
                "preamp-gain_mode": "LOW NOISE",
                "preamp-sensitivity_unit": "pA/V",
                "preamp-filter_lowpass": "  0.03 Hz",
                "preamp-offset_value": "1",
                "preamp-offset_sign": "+",
                "preamp-filter_type": "  No filter",
                "preamp-sensitivity_value": "1",
                "preamp-gain_db": 120.0,
                "preamp-bias_on": False,
                "preamp-offset_fine": 0,
                "preamp-invert": False,
                "preamp-filter_highpass": "  0.03 Hz",
                "preamp-gain_level": 27,
            },
            "timestamps": {
                "preamp-gain": 1785643843.042297,
                "preamp-blank": 1785643843.0424032,
                "preamp-bias_value": 1785643843.0423563,
                "preamp-offset_unit": 1785643843.0423398,
                "preamp-offset_on": 1785643843.0423138,
                "preamp-offset_cal": 1785643843.0423534,
                "preamp-gain_mode": 1785643843.042398,
                "preamp-sensitivity_unit": 1785643843.042297,
                "preamp-filter_lowpass": 1785643843.0423796,
                "preamp-offset_value": 1785643843.042331,
                "preamp-offset_sign": 1785643843.0423248,
                "preamp-filter_type": 1785643843.0423684,
                "preamp-sensitivity_value": 1785643843.042277,
                "preamp-gain_db": 1785643843.042297,
                "preamp-bias_on": 1785643843.0423589,
                "preamp-offset_fine": 1785643843.0423453,
                "preamp-invert": 1785643843.0424008,
                "preamp-filter_highpass": 1785643843.0423899,
                "preamp-gain_level": 1785643843.0423398,
            },
            "data_keys": {
                "preamp-gain": {
                    "dtype": "number",
                    "shape": [],
                    "dtype_numpy": "<f8",
                    "source": "mock+derived://preamp-gain",
                    "units": "V A⁻",
                },
                "preamp-blank": {
                    "dtype": "boolean",
                    "shape": [],
                    "dtype_numpy": "|b1",
                    "source": "mock+ca://25idc:SR570:blank_on",
                },
                "preamp-bias_value": {
                    "dtype": "integer",
                    "shape": [],
                    "dtype_numpy": "<i8",
                    "source": "mock+ca://25idc:SR570:bias_put",
                },
                "preamp-offset_unit": {
                    "dtype": "string",
                    "shape": [],
                    "dtype_numpy": "|S40",
                    "source": "mock+ca://25idc:SR570:offset_unit",
                    "choices": ["pA", "nA", "uA", "mA"],
                },
                "preamp-offset_on": {
                    "dtype": "boolean",
                    "shape": [],
                    "dtype_numpy": "|b1",
                    "source": "mock+ca://25idc:SR570:offset_on",
                },
                "preamp-offset_cal": {
                    "dtype": "string",
                    "shape": [],
                    "dtype_numpy": "|S40",
                    "source": "mock+ca://25idc:SR570:offset_cal",
                    "choices": ["CAL", "UNCAL"],
                },
                "preamp-gain_mode": {
                    "dtype": "string",
                    "shape": [],
                    "dtype_numpy": "|S40",
                    "source": "mock+ca://25idc:SR570:gain_mode",
                    "choices": ["LOW NOISE", "HIGH BW", "LOW DRIFT"],
                },
                "preamp-sensitivity_unit": {
                    "dtype": "string",
                    "shape": [],
                    "dtype_numpy": "|S40",
                    "source": "mock+ca://25idc:SR570:sens_unit",
                    "choices": ["pA/V", "nA/V", "uA/V", "mA/V"],
                },
                "preamp-filter_lowpass": {
                    "dtype": "string",
                    "shape": [],
                    "dtype_numpy": "|S40",
                    "source": "mock+ca://25idc:SR570:low_freq",
                    "choices": [
                        "  0.03 Hz",
                        "  0.1 Hz",
                        "  0.3 Hz",
                        "  1   Hz",
                        "  3   Hz",
                        " 10   Hz",
                        " 30   Hz",
                        "100   Hz",
                        "300   Hz",
                        "  1   kHz",
                        "  3   kHz",
                        " 10   kHz",
                        " 30   kHz",
                        "100   kHz",
                        "300   kHz",
                        "  1   MHz",
                    ],
                },
                "preamp-offset_value": {
                    "dtype": "string",
                    "shape": [],
                    "dtype_numpy": "|S40",
                    "source": "mock+ca://25idc:SR570:offset_num",
                    "choices": ["1", "2", "5", "10", "20", "50", "100", "200", "500"],
                },
                "preamp-offset_sign": {
                    "dtype": "string",
                    "shape": [],
                    "dtype_numpy": "|S40",
                    "source": "mock+ca://25idc:SR570:offset_sign",
                    "choices": ["+", "-"],
                },
                "preamp-filter_type": {
                    "dtype": "string",
                    "shape": [],
                    "dtype_numpy": "|S40",
                    "source": "mock+ca://25idc:SR570:filter_type",
                    "choices": [
                        "  No filter",
                        " 6 dB highpass",
                        "12 dB highpass",
                        " 6 dB bandpass",
                        " 6 dB lowpass",
                        "12 dB lowpass",
                    ],
                },
                "preamp-sensitivity_value": {
                    "dtype": "string",
                    "shape": [],
                    "dtype_numpy": "|S40",
                    "source": "mock+ca://25idc:SR570:sens_num",
                    "choices": ["1", "2", "5", "10", "20", "50", "100", "200", "500"],
                },
                "preamp-gain_db": {
                    "dtype": "number",
                    "shape": [],
                    "dtype_numpy": "<f8",
                    "source": "mock+derived://preamp-gain_db",
                    "units": "dB",
                },
                "preamp-bias_on": {
                    "dtype": "boolean",
                    "shape": [],
                    "dtype_numpy": "|b1",
                    "source": "mock+ca://25idc:SR570:bias_on",
                },
                "preamp-offset_fine": {
                    "dtype": "integer",
                    "shape": [],
                    "dtype_numpy": "<i8",
                    "source": "mock+ca://25idc:SR570:off_u_put",
                },
                "preamp-invert": {
                    "dtype": "boolean",
                    "shape": [],
                    "dtype_numpy": "|b1",
                    "source": "mock+ca://25idc:SR570:invert_on",
                },
                "preamp-filter_highpass": {
                    "dtype": "string",
                    "shape": [],
                    "dtype_numpy": "|S40",
                    "source": "mock+ca://25idc:SR570:high_freq",
                    "choices": [
                        "  0.03 Hz",
                        "  0.1 Hz",
                        "  0.3 Hz",
                        "  1   Hz",
                        "  3   Hz",
                        " 10   Hz",
                        " 30   Hz",
                        "100   Hz",
                        "300   Hz",
                        "  1   kHz",
                        "  3   kHz",
                        " 10   kHz",
                    ],
                },
                "preamp-gain_level": {
                    "dtype": "integer",
                    "shape": [],
                    "dtype_numpy": "<i8",
                    "source": "mock+derived://preamp-gain_level",
                },
            },
        }
    },
    "data_keys": {},
    "name": "primary",
    "object_keys": {"preamp": []},
    "run_start": "7b8014c3-c9cd-4349-9e81-6255f7e1306d",
    "time": 1785643862.6352003,
    "uid": "10f1145a-6a91-40c9-a742-9b7f5d109b1b",
    "hints": {"preamp": {}},
}
event_doc = {
    "uid": "70459839-fd78-4d34-b990-169381832f18",
    "time": 1785643862.6374788,
    "data": {},
    "timestamps": {},
    "seq_num": 1,
    "filled": {},
    "descriptor": "10f1145a-6a91-40c9-a742-9b7f5d109b1b",
}
stop_doc = {
    "uid": "892fa5da-74b3-473c-a158-0135f90458df",
    "time": 1785643862.6377752,
    "run_start": "7b8014c3-c9cd-4349-9e81-6255f7e1306d",
    "exit_status": "success",
    "reason": "",
    "num_events": {"primary": 1},
}


@pytest.mark.asyncio
async def test_stashes_recorded_uid():
    detector = soft_signal_rw(int)
    preamp = SR570PreAmplifier("", name="preamp")
    recorder = DarkCurrentRecorder(
        detectors=[detector],
        preamps=[preamp],
    )
    recorder.stash_dark_current("start", start_doc)
    recorder.stash_dark_current("descriptor", descriptor_doc)
    recorder.stash_dark_current("stop", stop_doc)
    assert recorder._scan_uid == start_doc["uid"]


@pytest.mark.asyncio
async def test_stashes_preamp_readings():
    detector = soft_signal_rw(int)
    preamp = SR570PreAmplifier("", name="preamp")
    recorder = DarkCurrentRecorder(
        detectors=[detector],
        preamps=[preamp],
    )
    recorder.stash_dark_current("start", start_doc)
    recorder.stash_dark_current("descriptor", descriptor_doc)
    recorder.stash_dark_current("stop", stop_doc)
    assert recorder._preamp_readings == {
        "preamp-sensitivity_value": "1",
        "preamp-sensitivity_unit": "pA/V",
        "preamp-offset_value": "1",
        "preamp-offset_unit": "pA",
        "preamp-offset_on": False,
        "preamp-offset_sign": "+",
        "preamp-invert": False,
    }


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
    recorder.stash_dark_current("start", start_doc)
    recorder.stash_dark_current("descriptor", descriptor_doc)
    recorder.stash_dark_current("stop", stop_doc)
    assert recorder._last_measured == pytest.approx(time.monotonic())


@pytest.mark.asyncio
async def test_warns_if_dark_current_fails(caplog):
    detector = soft_signal_rw(int)
    await detector.connect(mock=True)
    preamp = SR570PreAmplifier("", name="preamp")
    await preamp.connect(mock=True)
    recorder = DarkCurrentRecorder(
        detectors=[detector],
        preamps=[preamp],
    )
    recorder.stash_dark_current("start", start_doc)
    recorder.stash_dark_current("descriptor", descriptor_doc)
    with caplog.at_level(logging.WARNING):
        recorder.stash_dark_current("stop", {**stop_doc, "exit_status": "fail"})
    assert recorder._last_measured is None
    assert "Dark current may be measured again" in caplog.text


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
