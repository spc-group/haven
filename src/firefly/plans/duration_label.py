import math
from collections.abc import Mapping

import numpy as np
from pydantic import BaseModel, computed_field
from qtpy import QtWidgets
from scanspec.core import Axis, Path
from scanspec.specs import Spec

HALF_SPACE = "\u202f"


class Duration(BaseModel):
    livetime: float
    """The time during which the detectors are live."""

    movetime: float
    """The time during which the motors are moving from one point to
    another."""

    @computed_field
    def scantime(self) -> float:
        return self.livetime + self.movetime

    @computed_field
    def efficiency(self) -> float:
        """What portion of the total scan time is actual detector live time."""
        return self.livetime / self.scantime if self.scantime != 0 else float("nan")


def duration_from_spec(spec: Spec, velocities: Mapping[Axis, float]) -> Duration:
    """Calculate the duration a scan will take given it's scanspec."""
    slc = Path(spec.calculate()).consume()
    # Livetime is just the sum of all durations
    live_time = sum(slc.duration)
    # Movetime is how long it takes motors to move between points
    distances = {
        ax: slc.lower[ax][1:] - slc.upper[ax][:-1] for ax in slc.midpoints.keys()
    }
    move_times = {
        ax: abs(distances[ax]) / velocities.get(ax, float("inf"))
        for ax in distances.keys()
    }
    move_time: float = np.sum(np.max(np.asarray([*move_times.values()]), axis=0))
    scan_time = live_time + move_time
    return Duration(
        livetime=live_time,
        movetime=move_time,
    )


class DurationLabel(QtWidgets.QLabel):
    """A label that shows individual hours, minutes, seconds, etc."""

    def set_seconds(self, seconds: float | int, efficiency: float | None = None):
        """Set the duraction, in seconds.

        Will update the text to show the new duration. If *efficiency*
        is provided, the number will be shown as a per cent (i.e. how
        much of the time is spent collecting data vs moving motors).

        """
        if math.isnan(seconds):
            text = f"–{HALF_SPACE}h –{HALF_SPACE}m –{HALF_SPACE}s"
        else:
            hours, more_seconds = divmod(seconds, 3600)
            minutes, more_seconds = divmod(more_seconds, 60)
            text = f"{int(hours)}{HALF_SPACE}h {int(minutes)}{HALF_SPACE}m {math.ceil(more_seconds)}{HALF_SPACE}s"
            if efficiency is not None and math.isfinite(efficiency):
                text += f" ({int(efficiency*100)}{HALF_SPACE}%)"
        self.setText(text)


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
