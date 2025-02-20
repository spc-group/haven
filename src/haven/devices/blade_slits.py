"""This is a copy of the apstools Slits support with signals for the tweak PV."""

import logging
import uuid
from collections.abc import Sequence
from typing import Hashable

from bluesky import plan_stubs as bps
from ophyd_async.core import StandardReadable, StandardReadableFormat, soft_signal_rw
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw

from haven.positioner import Positioner

__all__ = ["BladeSlits", "BladePair", "SlitsPositioner"]

log = logging.getLogger(__name__)


class SlitsPositioner(Positioner):
    def __init__(self, prefix: str, readback: str, name: str = ""):
        self.setpoint = epics_signal_rw(float, f"{prefix}.VAL")
        with self.add_children_as_readables():
            self.readback = epics_signal_r(float, readback)
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.units = epics_signal_rw(str, f"{prefix}.EGU")
            self.precision = epics_signal_rw(int, f"{prefix}.PREC")
        self.velocity = soft_signal_rw(int, initial_value=100)
        super().__init__(name=name)


class BladePair(StandardReadable):
    """A set of blades controlling beam size in one direction."""

    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables():
            self.size = SlitsPositioner(f"{prefix}size", readback=f"{prefix}t2.C")
            self.center = SlitsPositioner(f"{prefix}center", readback=f"{prefix}t2.D")
        super().__init__(name=name)


class BladeSlits(StandardReadable):
    """Set of slits with blades that move in and out to control beam
    size.

    """

    _ophyd_labels_ = {"slits"}

    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables():
            self.horizontal = BladePair(f"{prefix}H")
            self.vertical = BladePair(f"{prefix}V")
        super().__init__(name=name)


def setup_blade_slits(
    devices: Sequence[BladeSlits],
    precision: int = 0,
    group: Hashable | None = None,
    wait: bool = True,
):
    """Configures the blade slit devices for normal operation.

    - Set each position precision to ``0`` to match the motor precision.

    Parameters
    ==========
    devices
      The blade slit devices to update.
    precision
      The precision for the setpoint of all the slits' positioners.
    group
      Identifier used by ‘wait’
    wait
      If True, wait for completion before processing any more
      messages. True by default.

    """
    if wait and group is None:
        group = str(uuid.uuid4())
    for device in devices:
        positioners = [
            device.horizontal.center,
            device.horizontal.size,
            device.vertical.center,
            device.vertical.size,
        ]
        for positioner in positioners:
            yield from bps.abs_set(
                positioner.precision, precision, wait=False, group=group
            )
    if wait:
        yield from bps.wait(group=group)


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
