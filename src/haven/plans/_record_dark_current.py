import uuid
from typing import Sequence

from bluesky import Msg
from bluesky import plan_stubs as bps
from bluesky import plans as bp
from bluesky import preprocessors as bpp
from ophyd import Device

from ..devices import IonChamber
from ..devices.shutter import ShutterState
from ..instrument import beamline
from ._shutters import close_shutters, open_shutters


def count_is_complete(*, old_value, value, **kwargs):
    """Check if the value is done."""
    was_running = old_value == 1
    is_running_now = value == 1
    is_done = was_running and not is_running_now
    return is_done


def record_dark_current(detectors: Sequence[Device], shutters: Sequence[Device] = []):
    """Record the dark current on the ion chambers.

    - Close shutters
    - Trigger detectors
    - Calibrate to make readings zero
    - Restore shutters to their previous positions

    Parameters
    ==========
    detectors
      Ion chamber devices or names.
    shutters
      Shutter devices or names. These shutters will be closed before
      recording the dark current, and then be returned to its original
      state afterward recording the dark current.

    """
    detectors = beamline.devices.findall(detectors)
    _md = {
        "detectors": [det.name for det in detectors],
        "num_points": 1,
        "num_intervals": 0,
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "shutters": list(map(repr, shutters)),
        },
        "plan_name": "record_dark_current",
        "hints": {},
    }

    @bpp.stage_decorator([*detectors, *shutters])
    def inner():
        # Get previous shutter states
        old_shutters = {}
        for shutter in shutters:
            old_shutters[shutter] = yield from bps.rd(shutter.readback)
        # Close shutters
        yield from close_shutters(shutters)
        # Old-style ion chambers need to be handled differently
        old_ion_chambers = [ic for ic in detectors if isinstance(ic, IonChamber)]
        new_detectors = [ic for ic in detectors if not isinstance(ic, IonChamber)]
        # Record dark currents
        group = uuid.uuid4()
        for ic in old_ion_chambers:
            yield Msg("trigger", ic, group=group, record_dark_current=True)
        yield from bpp.run_wrapper(
            bpp.stub_wrapper(bp.count([*new_detectors, *shutters])), md=_md
        )
        # Wait for the devices to be done recording dark current
        yield from bps.wait(group=group)
        # Calibrate standard detectors to they read zero
        for detector in new_detectors:
            yield Msg("calibrate", detector, truth=0)
        # Reset shutters to their original states
        to_open = [
            sht
            for sht, old_state in old_shutters.items()
            if old_state == ShutterState.OPEN
        ]
        yield from open_shutters(to_open)

    yield from inner()


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
