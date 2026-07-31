import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from bluesky import plan_stubs as bps
from bluesky.protocols import Readable

from haven.devices import SRS570PreAmplifier as SR570PreAmplifier
from haven.plans._record_dark_current import record_dark_current

TEN_MINUTES = 600


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

    def preamp_readings(self):
        """Measure the state of all the preamps for comparison."""
        reading = {}
        signals = [
            "sensitivity_unit",
            "sensitivity_value",
            "offset_value",
            "offset_unit",
            "offset_on",
            "offset_sign",
            "invert",
        ]
        signals = [getattr(preamp, sig) for preamp in self.preamps for sig in signals]
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
        # Call the original plan as intended
        yield from plan


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
