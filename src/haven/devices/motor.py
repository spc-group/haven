import logging
from collections.abc import Generator

from ophyd_async.core import (
    AsyncStatus,
    FlyMotorInfo,
    StandardReadableFormat,
    StrictEnum,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw
from ophyd_async.epics.motor import Motor as MotorBase

from haven.devices.undulator import TrajectoryMotorInfo

log = logging.getLogger(__name__)


class Motor(MotorBase):
    """The default motor for asynchrnous movement."""

    _ophyd_labels_: set[str]

    class Direction(StrictEnum):
        POSITIVE = "Pos"
        NEGATIVE = "Neg"

    def __init__(self, prefix: str, name="", labels={"motors"}):
        self._ophyd_labels_ = labels
        # Configuration signals
        with self.add_children_as_readables(StandardReadableFormat.CONFIG_SIGNAL):
            self.description = epics_signal_rw(str, f"{prefix}.DESC")
            self.offset_dir = epics_signal_rw(self.Direction, f"{prefix}.DIR")
        # Motor status signals
        self.motor_is_moving = epics_signal_r(int, f"{prefix}.MOVN")
        self.direction_of_travel = epics_signal_r(int, f"{prefix}.TDIR")
        self.soft_limit_violation = epics_signal_r(int, f"{prefix}.LVIO")
        # Load all the parent signals
        super().__init__(prefix=prefix, name=name)

    async def connect(self, *args, **kwargs):
        await super().connect(*args, **kwargs)
        await self.description.set(self.name)

    @AsyncStatus.wrap
    async def prepare(self, value: FlyMotorInfo | TrajectoryMotorInfo):
        if isinstance(value, FlyMotorInfo):
            return await super().prepare(value)


def load_motors(**defns: str) -> Generator[Motor, None, None]:
    """Batch-create several motors.

    Each entry in `**defns` is a motor, so the following statements
    are equivalent.

    ..code-block :: python

        # Create all at once
        list(load_motors(m1="255idcVME:m1", m2="255idcVME:m2"))
        # Create each motor individually
        [Motor("255idcVME:m1", name="m1"), Motor("255idcVME:m2", name="m2")]

    """
    for name, prefix in defns.items():
        yield Motor(prefix, name=name, labels={"motors", "extra_motors"})


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
