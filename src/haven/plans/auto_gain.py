from queue import Queue

import numpy as np
import pandas as pd
from bluesky import plan_stubs as bps
from bluesky import plans as bp
from bluesky.callbacks.core import CollectThenCompute
from bluesky.preprocessors import subs_decorator
from bluesky_adaptive.per_event import adaptive_plan, recommender_factory
from bluesky_adaptive.recommendations import NoRecommendation
from ophyd.sim import motor

from ..instrument.instrument_registry import registry


__all__ = ["GainRecommender", "auto_gain"]


class GainRecommender:
    """A recommendation engine for finding the best ion chamber gain*.

    Responds to ion chamber voltage as the dependent variable but
    changing the gain. If the voltage is above *volts_max* then the
    next gain* level will be one higher, and if the voltage is below
    *volts_min* then the next gain* level will be one lower.

    *Gain is actually sensitivity in the case of an SRS-570 preamp, so
     raising the sensitivity results in a lower gain.

    """

    volts_min: float
    volts_max: float
    gain_max: int = 28
    last_point: np.ndarray = None

    def __init__(self, volts_min: float = 0.5, volts_max: float = 4.5):
        self.volts_min = volts_min
        self.volts_max = volts_max

    def tell(self, gains, volts):
        new_gains = np.copy(gains)
        # Adjust new_gains for devices that are out of range, with hysteresis
        if self.last_point is None:
            is_hysteretical = np.full_like(gains, True, dtype=bool)
        else:
            is_hysteretical = gains < self.last_point
        self.last_point = gains        
        is_low = volts < self.volts_min
        new_gains[np.logical_or(is_low, is_hysteretical)] -= 1
        is_high = volts > self.volts_max
        new_gains[is_high] += 1
        # Ensure we're within the bounds for gain values
        new_gains[new_gains<0] = 0
        new_gains[new_gains>self.gain_max] = self.gain_max
        # Check whether we need to move to a new point of not
        if np.logical_or(is_low, is_high).any():
            self.next_point = new_gains
        else:
            self.next_point = None

    def tell_many(self, xs, ys):
        for x, y in zip(xs, ys):
            self.tell(x, y)

    def ask(self, n, tell_pending=True):
        if n != 1:
            raise NotImplementedError
        if self.next_point is None:
            raise NoRecommendation
        return self.next_point


def auto_gain(
    dets="ion_chambers",
    volts_min: float = 0.5,
    volts_max: float = 4.5,
    max_count: int = 28,
    queue: Queue = None,
):
    """An adaptive Bluesky plan for optimizing pre-amp gains.

    At each step, the plan will measure the pre-amp voltage via the
    scaler. If the measured voltage for a pre-amp is outside the range
    (*volts_min*, *volts_max*), then the gain for the next step will
    be adjusted by one level. Once all detectors are within the
    optimal range (or *max_count* iterations have been done), the scan
    will end.

    Parameters
    ==========
    dets
      A sequence of detectors to scan. Can be devices, names, or Ophyd
      labels.
    volts_min
      The minimum acceptable range for each ion chamber's voltage.
    volts_max
      The maximum acceptable range for each ion chamber's voltage.
    max_count
      The scan will end after *max_count* iterations even if an
      optimal gain has not been found for all pre-amps.
    queue
      [Testing] A Queue object for passing recommendations between the
      plan and the recommendation engine.

    """
    # Resolve the detector list into real devices
    dets = registry.findall(dets)
    # Prepare the recommendation enginer
    recommender = GainRecommender(volts_min=volts_min, volts_max=volts_max)
    ind_keys = [det.preamp.sensitivity_level.name for det in dets]
    dep_keys = [det.volts.name for det in dets]
    rr, queue = recommender_factory(
        recommender,
        independent_keys=ind_keys,
        dependent_keys=dep_keys,
        max_count=max_count,
        queue=queue,
    )
    # Start from the current gain settings
    first_point = {
        det.preamp.sensitivity_level: det.preamp.sensitivity_level.get() for det in dets
    }
    # Make sure the detectors have the correct read attrs.
    old_kinds = {}
    signals = [(det.preamp, det.preamp.sensitivity_level) for det in dets]
    signals = [sig for tpl in signals for sig in tpl]
    for sig in signals:
        old_kinds[sig] = sig.kind
        sig.kind = "normal"
    # Execute the adaptive plan
    try:
        yield from adaptive_plan(
            dets=dets, first_point=first_point, to_recommender=rr, from_recommender=queue
        )
    finally:
        # Restore the detector signal kinds
        for sig in signals:
            sig.kind = old_kinds[sig]


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
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
