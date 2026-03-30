import logging
from collections.abc import Sequence

from ophyd_async.core import (
    DeviceVector,
    StandardReadable,
)
from ophyd_async.core import StandardReadableFormat as Format
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw

from haven.devices import Motor

log = logging.getLogger(__name__)


# LOAD_TIMEOUT = 80


class Sample(StandardReadable):
    """An individual robot sample that can be loaded.

    Signals
    =======
    present
      Whether or not a sample is physically present on the stage.
    empty
      Whether or not no sample is physically present on the stage.
    load
      Direct the robot to physically move this sample to the loading
      position. Can be slow (~25-30 seconds).
    unload
      Direct the robot to physically remove this sample to the loading
      position. Can be slow (~25-30 seconds).
    x
      The x position of the robot in Cartesian coordinates.
    y
      The y position of the robot in Cartesian coordinates.
    z
      The z position of the robot in Cartesian coordinates.
    rx
      The rx position of the robot in Cartesian coordinates.
    ry
      The ry position of the robot in Cartesian coordinates.
    rz
      The position of the robot in Cartesian coordinates.

    """

    def __init__(self, prefix: str, *, name: str = ""):
        with self.add_children_as_readables():
            self.present = epics_signal_r(float, f"{prefix}:present")
            self.empty = epics_signal_r(float, f"{prefix}:empty")
            self.x = epics_signal_r(float, f"{prefix}:x")
            self.y = epics_signal_r(float, f"{prefix}:y")
            self.z = epics_signal_r(float, f"{prefix}:z")
            self.rx = epics_signal_r(float, f"{prefix}:rx")
            self.ry = epics_signal_r(float, f"{prefix}:ry")
            self.rz = epics_signal_r(float, f"{prefix}:rz")

        self.load = epics_signal_rw(
            float,
            f"{prefix}:load",
            # write_timeout=LOAD_TIMEOUT,
            # put_complete=True,
        )
        self.unload = epics_signal_rw(
            float,
            f"{prefix}:unload",
            # write_timeout=LOAD_TIMEOUT,
            # put_complete=True,
        )
        super().__init__(name=name)


DEFAULT_SAMPLES = [8, 9, 10, 14, 15, 16, 20, 21, 22]


class Robot(StandardReadable):
    _ophyd_labels_ = {"robots"}

    def __init__(
        self, prefix: str, *, name: str = "", samples: Sequence[int] = DEFAULT_SAMPLES
    ):
        with self.add_children_as_readables():
            # Joints and positions
            self.i = Motor(f"{prefix}:i")
            self.j = Motor(f"{prefix}:i")
            self.k = Motor(f"{prefix}:i")
            self.l = Motor(f"{prefix}:i")
            self.m = Motor(f"{prefix}:i")
            self.n = Motor(f"{prefix}:i")
            self.x = Motor(f"{prefix}:i")
            self.y = Motor(f"{prefix}:i")
            self.z = Motor(f"{prefix}:i")
            self.rx = Motor(f"{prefix}:i")
            self.ry = Motor(f"{prefix}:i")
            self.rz = Motor(f"{prefix}:i")
            self.gripper_rbv = epics_signal_rw(float, f"{prefix}:gripper.RBV")
            self.gripper_val = epics_signal_rw(float, f"{prefix}:gripper.VAL")
            self.samples = DeviceVector(
                {n: Sample(f"{prefix}:sample{n}") for n in samples}
            )

        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.acc = epics_signal_rw(float, f"{prefix}:acceleration")
            self.vel = epics_signal_rw(float, f"{prefix}:velocity")
            self.remote_control = epics_signal_r(
                float, f"{prefix}:dashboard:remote_control"
            )
            self.program_rbv = epics_signal_r(float, f"{prefix}:dashboard:program_rbv")
            self.installation = epics_signal_rw(
                float, f"{prefix}:dashboard:installation"
            )
            self.close_safety_popup = epics_signal_rw(
                float, f"{prefix}:dashboard:close_safety_popup"
            )
            self.unlock_protective_stop = epics_signal_rw(
                float, f"{prefix}:dashboard:unlock_protective_stop"
            )
            self.restart_safety = epics_signal_rw(
                float, f"{prefix}:dashboard:restart_safety"
            )
            self.program_running = epics_signal_rw(
                float, f"{prefix}:dashboard:program_running"
            )
            self.safety_status = epics_signal_rw(
                float, f"{prefix}:dashboard:safety_status"
            )
            self.power_rbv = epics_signal_r(float, f"{prefix}:dashboard:power_rbv")
            self.gripper_activated = epics_signal_rw(float, f"{prefix}:gripper.ACR")
            self.gripper_force = epics_signal_rw(float, f"{prefix}:gripper.FRC")
            self.current_sample = epics_signal_r(float, f"{prefix}:current_sample")
            self.home = epics_signal_rw(float, f"{prefix}:home")
            self.cal_stage = epics_signal_rw(float, f"{prefix}:cal_stage")

        self.power = epics_signal_rw(float, f"{prefix}:dashboard:power")
        self.program = epics_signal_rw(float, f"{prefix}:dashboard:program_rbv")
        self.playRbt = epics_signal_rw(float, f"{prefix}:dashboard:play")
        self.stopRbt = epics_signal_rw(float, f"{prefix}:dashboard:stop")
        self.pauseRbt = epics_signal_rw(float, f"{prefix}:dashboard:pause")
        self.quitRbt = epics_signal_rw(float, f"{prefix}:dashboard:quit")
        self.shutdown = epics_signal_rw(float, f"{prefix}:dashboard:shutdown")
        self.release_brake = epics_signal_rw(float, f"{prefix}:dashboard:release_brake")

        # gripper
        self.gripper_activate = epics_signal_rw(float, f"{prefix}:gripper.ACT")
        self.gripper_close = epics_signal_rw(float, f"{prefix}:gripper.CLS")
        self.gripper_open = epics_signal_rw(float, f"{prefix}:gripper.OPN")

        self.busy = epics_signal_rw(float, f"{prefix}:busy")

        # sample transfer
        #   unload_current_sample ophyd device used write_timeout=LOAD_TIMEOUT, put_complete=True
        self.unload_current_sample = epics_signal_rw(
            float, f"{prefix}:unload_current_sample"
        )
        self.current_sample_reset = epics_signal_rw(
            float, f"{prefix}:current_sample_reset"
        )

        super().__init__(name=name)


# -----------------------------------------------------------------------------
# :author:    Yanna Chen
# :email:     yannachen@anl.gov
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
