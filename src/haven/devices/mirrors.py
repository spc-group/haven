from apstools.synApps import TransformRecord
from ophyd_async.core import Device

from .motor import Motor
from .transform import TransformRecord


class HighHeatLoadMirror(Device):
    """A single mirror, controlled by several motors.

    Possibly also bendable.
    """

    _ophyd_labels_ = {"mirrors"}

    def __init__(self, prefix: str, name: str = "", bendable=False):
        # Physical motors
        self.transverse = Motor(f"{prefix}m1")
        self.roll = Motor(f"{prefix}m2")
        self.upstream = Motor(f"{prefix}m3")
        self.downstream = Motor(f"{prefix}m4")

        # Pseudo motors
        self.pitch = Motor(f"{prefix}coarsePitch")
        self.normal = Motor(f"{prefix}lateral")

        # Standard transform records for the pseudo motors
        self.drive_transform = TransformRecord(f"{prefix}lats:Drive")
        self.readback_transform = TransformRecord(f"{prefix}lats:Readback")

        if bendable:
            self.bender = Motor(f"{prefix}m5")

        super().__init__(name=name)


class KBMirror(Device):
    """A single mirror in a KB mirror set."""

    def __init__(
        self,
        prefix: str,
        upstream_motor: str,
        downstream_motor: str,
        upstream_bender: str = "",
        downstream_bender: str = "",
        name: str = "",
    ):
        self.pitch = Motor(f"{prefix}pitch")
        self.normal = Motor(f"{prefix}height")
        self.upstream = Motor(upstream_motor)
        self.downstream = Motor(downstream_motor)
        if upstream_bender != "":
            self.bender_upstream = Motor(upstream_bender)
        if downstream_bender != "":
            self.bender_downstream = Motor(downstream_bender)
        # The pseudo motor transform records have
        # a missing ':', so we need to remove it.
        transform_prefix = "".join(prefix.rsplit(":", 2))
        self.drive_transform = TransformRecord(f"{transform_prefix}:Drive")
        self.readback_transform = TransformRecord(f"{transform_prefix}:Readback")
        super().__init__(name=name)


class KBMirrors(Device):
    _ophyd_labels_ = {"kb_mirrors"}

    def __init__(
        self,
        prefix: str,
        horiz_upstream_motor: str,
        horiz_downstream_motor: str,
        vert_upstream_motor: str,
        vert_downstream_motor: str,
        horiz_upstream_bender: str = "",
        horiz_downstream_bender: str = "",
        vert_upstream_bender: str = "",
        vert_downstream_bender: str = "",
        name: str = "",
    ):
        # Create the two sub-mirrors
        self.horiz = KBMirror(
            prefix=f"{prefix}H:",
            upstream_motor=horiz_upstream_motor,
            downstream_motor=horiz_downstream_motor,
            upstream_bender=horiz_upstream_bender,
            downstream_bender=horiz_downstream_bender,
        )
        self.vert = KBMirror(
            prefix=f"{prefix}V:",
            upstream_motor=vert_upstream_motor,
            downstream_motor=vert_downstream_motor,
            upstream_bender=vert_upstream_bender,
            downstream_bender=vert_downstream_bender,
        )
        super().__init__(name=name)


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
