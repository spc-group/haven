from collections.abc import Generator, Sequence
from functools import partial
from typing import Any

from bluesky import Msg
from bluesky import plan_stubs as bps
from bluesky import preprocessors as bpp
from bluesky.suspenders import SuspendFloor as BlueskySuspendFloor
from bluesky.suspenders import SuspendWhenChanged as BlueskySuspendWhenChanged
from bluesky.utils import make_decorator
from ophyd_async.core import Device

from haven.devices import ApsMachine
from haven.plans._shutters import open_shutters

RESUME_TIME = 120


class NewSuspenderShim:
    # This is a work-around for using ophyd-async (new-style
    # Subscribable) with Bluesky (old-style Subscribable) until this
    # is fixed upstream
    # https://github.com/bluesky/bluesky/pull/1923
    def install(self, RE, *, event_type=None):
        """Install callback on signal

        This (re)installs the required callbacks at the pyepics level

        Parameters
        ----------

        RE : RunEngine
            The run engine instance this should work on

        event_type : str, optional
            The event type (subscription type) to watch
        """
        with self._lock:
            self.RE = RE
        self._sig.subscribe_reading(self)

    def _should_suspend(self, value):
        # *value* is actually a reading, so convert
        value = value[self._sig.name]["value"]
        return super()._should_suspend(value)

    def _should_resume(self, value):
        # *value* is actually a reading, so convert
        value = value[self._sig.name]["value"]
        return super()._should_resume(value)


class SuspendWhenChanged(NewSuspenderShim, BlueskySuspendWhenChanged):
    def _get_justification(self):
        if not self.tripped:
            return ""

        just = f'Signal {self._sig.name}, got "<redacted>", expected "{self.expected_value}"'
        if not self.allow_resume:
            just += '.  "RE.abort()" and then restart session to use new configuration.'
        return ": ".join(s for s in (just, self._tripped_message) if s)


class SuspendFloor(NewSuspenderShim, BlueskySuspendFloor):
    def _get_justification(self):
        if not self.tripped:
            return ""

        just = (
            f"Signal {self._sig.name} = <redacted> "
            + f"fell below {self._suspend_thresh} "
            + f"and has not yet crossed above {self._resume_thresh}."
        )
        return ": ".join(s for s in (just, self._tripped_message) if s)


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
