import logging
import time
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field

from bluesky import Msg
from bluesky import plan_stubs as bps
from bluesky import preprocessors as bpp
from bluesky.protocols import Readable

from haven.devices import SRS570PreAmplifier as SR570PreAmplifier
from haven.plans._record_dark_current import record_dark_current

TEN_MINUTES = 600

PREAMP_SIGNALS: Sequence[str] = [
    "sensitivity_unit",
    "sensitivity_value",
    "offset_value",
    "offset_unit",
    "offset_on",
    "offset_sign",
    "invert",
]


log = logging.getLogger()


@dataclass
class DarkCurrentRecorder:
    """Automatically measure dark current when needed and inject UID
    as metadata.

    This preprocessor will inject messages to record the dark current
    when either of the following are true.

    If will also add metadata ("dark_current_uid") into the start
    document of each run with the UID of the last dark current
    measurement.

    1. It has been longer than *time_to_live* seconds ago since the
       last time the dark current was measured.
    2. Any of the gain or offset settings for any of *preamps* have
       been changed since the last time the dark current was recorded.

    Usage
    =====

    ```python
    recorder = DarkCurrentRecorder(...)

    # Subscribe so we can spy on when dark current is recorded
    # RE.subscribe(wrapper.stash_dark_current)

    # Wrap your plan to do checks and inject metadata
    plan = recorder(bp.count(...))
    ```

    """

    detectors: Sequence[Readable]
    preamps: Sequence[SR570PreAmplifier]
    time_to_live: int | float = TEN_MINUTES
    _last_measured: int | float | None = None
    _preamp_readings: dict = field(default_factory=dict)
    _scan_uid: str | None = None
    _pending: dict = field(default_factory=dict)
    _is_subscribed: bool = False

    def preamp_readings(self):
        """Measure the state of all the preamps for comparison."""
        reading = {}
        signals = [
            getattr(preamp, sig) for preamp in self.preamps for sig in PREAMP_SIGNALS
        ]
        for signal in signals:
            reading[signal.name] = yield from bps.rd(signal)
        return reading

    def __call__(self, plan):
        """Wrap a plan and insert dark current messages and metadata."""
        # Check various conditions to see if we need a new reading
        needs_dark_current = False
        if self._last_measured is None:
            needs_dark_current = True
        else:
            expires = self._last_measured + self.time_to_live
            now = time.monotonic()
            needs_dark_current = needs_dark_current or now > expires
        # We need to record dark current if the preamps have been changed
        reading = yield from self.preamp_readings()
        preamps_changed = reading != self._preamp_readings
        needs_dark_current = needs_dark_current or preamps_changed
        # Make the dark current reading if needed
        if needs_dark_current:
            yield from record_dark_current(detectors=self.detectors)
        # If we're subscribed to the run engine, we should at least
        # see messages from the `record_dark_current()` plan above.
        if not self._is_subscribed:
            warnings.warn(
                f"{repr(self.stash_dark_current)} is not subscribed to the run engine."
            )
        # Call the original plan as intended
        yield from bpp.msg_mutator(plan, self.inject_dark_current_uid)

    def inject_dark_current_uid(self, msg: Msg) -> Msg:
        if self._scan_uid is None or msg.command != "open_run":
            return msg
        if msg.kwargs.get("plan_name") == "record_dark_current":
            return msg
        # Valid open-run message, so add in the metadata
        new_kwargs = {"dark_current_uid": self._scan_uid, **msg.kwargs}
        new_msg = Msg(
            command=msg.command,
            obj=msg.obj,
            *msg.args,
            **new_kwargs,
            run=msg.run,
        )
        return new_msg

    def stash_dark_current(self, name, doc) -> None:
        """A callback that stashes information about recorded dark currents.

        Usage
        =====

        ```
        recorder = DarkCurrentRecorder(...)
        RE.subscribe(recorder.stash_dark_current)
        ```

        """
        # If we receive any documents, we have to be subscribed to a
        # run engine
        self._is_subscribed = True
        if name == "start" and doc.get("plan_name") == "record_dark_current":
            self._pending = {"start_uid": doc["uid"]}
            return
        if doc.get("run_start") != self._pending.get("start_uid"):
            # We only care about docs that are part of the record_dark_current plan
            return
        if name == "descriptor":
            # Store preamp readings so we can tell when they've been changed
            self._pending["preamp_readings"] = {}
            for preamp in self.preamps:
                sigs = [getattr(preamp, sig_name) for sig_name in PREAMP_SIGNALS]
                config = doc["configuration"][preamp.name]["data"]
                self._pending["preamp_readings"].update(
                    {sig.name: config[sig.name] for sig in sigs}
                )
        # We only want to stash the dark current metadata if the run was successful
        is_stop_doc = name == "stop"
        exit_status = doc.get("exit_status")
        if is_stop_doc and exit_status == "success":
            # Maybe we didn't actually get all the info we need for some reason
            missing_keys = [
                key
                for key in ["start_uid", "preamp_readings"]
                if key not in self._pending
            ]
            if any(missing_keys):
                log.warning(
                    f"Cannot find {missing_keys} for dark current run {doc.get('run_start')}"
                )
                return
            self._scan_uid = self._pending["start_uid"]
            self._preamp_readings = self._pending["preamp_readings"]
            self._last_measured = time.monotonic()
        if is_stop_doc and exit_status != "success":
            # Failed run, so we won't stash anything, just clean up and report
            log.warning(
                f"Run '{self._pending['start_uid']}' completed with status {repr(doc.get('exit_status'))}."
                " Dark current may be measured again next run."
            )
            self._pending = dict()


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
