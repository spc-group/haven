from typing import Mapping

from apstools.synApps import TransformRecord
from ophyd_async.core import Device

from .. import exceptions
from .._iconfig import load_config
from .device import connect_devices
from .instrument_registry import InstrumentRegistry
from .instrument_registry import registry as default_registry
from .motor import Motor
from .transform import TransformRecord


class HighHeatLoadMirror(Device):
    """A single mirror, controlled by several motors.

    Possibly also bendable.
    """

    ophyd_labels_ = {"mirrors"}

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

    ophyd_labels_ = {"mirrors"}

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


async def load_mirrors(
    config: Mapping = None,
    registry: InstrumentRegistry = default_registry,
    connect: bool = True,
):
    if config is None:
        config = load_config()
    # Create two-bounce KB mirror sets
    devices = []
    for name, kb_config in config.get("kb_mirrors", {}).items():
        # Build the motor prefixes
        try:
            prefix = kb_config["prefix"]
            ioc_prefix = prefix.split(":")[0]
            motors = dict(
                # Normal motors
                horiz_upstream_motor=kb_config["horiz_upstream_motor"],
                horiz_downstream_motor=kb_config["horiz_downstream_motor"],
                vert_upstream_motor=kb_config["vert_upstream_motor"],
                vert_downstream_motor=kb_config["vert_downstream_motor"],
                # Bender motors
                horiz_upstream_bender=kb_config.get("horiz_upstream_bender", ""),
                horiz_downstream_bender=kb_config.get("horiz_downstream_bender", ""),
                vert_upstream_bender=kb_config.get("vert_upstream_bender", ""),
                vert_downstream_bender=kb_config.get("vert_downstream_bender", ""),
            )
            # Convert motors to fully qualified PV names (if not empty)
            motors = {
                key: f"{ioc_prefix}:{val}" for key, val in motors.items() if bool(val)
            }
        except KeyError as ex:
            raise exceptions.UnknownDeviceConfiguration(
                f"Device {name} missing '{ex.args[0]}': {kb_config}"
            )
        # Make the device
        devices.append(KBMirrors(prefix=prefix, name=name, **motors))
    # Create single-bounce mirrors
    for name, mirror_config in config.get("mirrors", {}).items():
        # Decide which base class of mirror to use
        DeviceClass = globals().get(mirror_config["device_class"])
        # Check that it's a valid device class
        if DeviceClass is None:
            msg = f"mirrors.{name}.device_class={mirror_config['device_class']}"
            raise exceptions.UnknownDeviceConfiguration(msg)
        devices.append(
            DeviceClass(
                prefix=mirror_config["prefix"],
                bendable=mirror_config["bendable"],
                name=name,
            )
        )
    if connect:
        devices = await connect_devices(
            devices, mock=not config["beamline"]["is_connected"], registry=registry
        )
    return devices


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
