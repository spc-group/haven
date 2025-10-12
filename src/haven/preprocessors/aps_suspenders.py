from collections.abc import Generator, Sequence
from functools import partial
from typing import Any

from bluesky import Msg
from bluesky import plan_stubs as bps
from bluesky import preprocessors as bpp
from bluesky.suspenders import SuspendFloor, SuspendWhenChanged
from bluesky.utils import make_decorator
from ophyd_async.core import Device

from haven._iconfig import load_config
from haven.devices import ApsMachine
from haven.plans._shutters import open_shutters

RESUME_TIME = 120


def aps_suspenders_wrapper(
    plan: Generator[Msg, Any, Any],
    aps: ApsMachine,
    minimum_current: int | float = 30,
    sleep: int | float = 120,
    shutters: Sequence[Device] = (),
) -> Generator[Msg, Any, Any]:
    """Before the plan starts, install suspenders for the APS storage ring.

    If the current falls below *minimum_current*, or the shutter
    permit is revoked, the run engine will suspend, and resume *sleep*
    seconds after the storage ring becomes usable again.

    Suspenders are removed at the end of the plan.

    """
    suspenders = []  # Needs to be here so we can clean up after the plan
    open_these_shutters = partial(open_shutters, shutters=shutters)

    def install_suspenders():
        if not load_config().feature_flag("install_storage_ring_suspenders"):
            yield from plan
            return
        # If we start a scan outside of user mode, we're probably testing
        in_user_operations = (yield from bps.rd(aps.machine_status)) not in [
            "ASD Studies",
            "MAINTENANCE",
        ]
        if in_user_operations:
            suspenders.extend(
                [
                    SuspendWhenChanged(
                        signal=aps.shutter_status,
                        expected_value="PERMIT",
                        allow_resume=True,
                        sleep=sleep,
                        tripped_message="Shutter permit revoked.",
                        post_plan=open_these_shutters,
                    ),
                    SuspendFloor(
                        signal=aps.current,
                        suspend_thresh=minimum_current,
                        sleep=sleep,
                    ),
                ]
            )
            for suspender in suspenders:
                yield from bps.install_suspender(suspender)
        yield from plan

    def remove_suspenders(suspenders):
        for suspender in suspenders:
            yield from bps.remove_suspender(suspender)

    return bpp.finalize_wrapper(
        install_suspenders(), partial(remove_suspenders, suspenders=suspenders)
    )


aps_suspenders_decorator = make_decorator(aps_suspenders_wrapper)

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
