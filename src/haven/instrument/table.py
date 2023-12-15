import asyncio

from ophyd import Device, Component as Cpt, FormattedComponent as FCpt, Kind, OphydObj
from apstools.synApps import TransformRecord

from .device import aload_devices, make_device
from .._iconfig import load_config
from .. import exceptions
from .motor import HavenMotor


class Table(Device):
    """A dynamic Ophyd device for an optical table.

    This device will have the components needed for the configuration
    of motors provided. For example, if *horizontal_motor* is
    provided, then the device will have a ``horizontal`` attribute
    that is the corresponding horizontal motor.
    
    """

    # These are the possible components that could be present
    vertical: OphydObj
    horizontal: OphydObj
    upstream: OphydObj
    downstream: OphydObj
    pitch: OphydObj
    horizontal_drive_transform: OphydObj
    horizontal_readback_transform: OphydObj
    
    def __new__(
        cls,
        prefix,
        *args,
        vertical_motor: str = "",
        horizontal_motor: str = "",
        upstream_motor: str = "",
        downstream_motor: str = "",
        **kwargs,
    ):
        # See if we have direct control over the vertical/horizontal positions
        comps = {}
        if bool(vertical_motor):
            comps["vertical"] = FCpt(
                HavenMotor,
                "{self.motor_prefix}:{self._vertical_motor}",
                labels={"motors"},
            )
        if bool(horizontal_motor):
            comps["horizontal"] = FCpt(
                HavenMotor,
                "{self.motor_prefix}:{self._horizontal_motor}",
                labels={"motors"},
            )
        if bool(upstream_motor):
            comps["upstream"] = FCpt(
                HavenMotor,
                "{self.motor_prefix}:{self._upstream_motor}",
                labels={"motors"},
            )
        if bool(downstream_motor):
            comps["downstream"] = FCpt(
                HavenMotor,
                "{self.motor_prefix}:{self._downstream_motor}",
                labels={"motors"},
            )
        # Check if we need to add the pseudo motors and tranforms
        if bool(upstream_motor) and bool(downstream_motor):
            comps["vertical"] = Cpt(
                HavenMotor,
                "height",
                labels={"motors"}
            )
            comps["pitch"] = Cpt(
                HavenMotor,
                "pitch",
                labels={"motors"}
            )
            comps["vertical_drive_transform"] = FCpt(
                TransformRecord,
                "{self.transform_prefix}:Drive",
                kind=Kind.config
            )
            comps["vertical_readback_transform"] = FCpt(
                TransformRecord,
                "{self.transform_prefix}:Readback",
                kind=Kind.config
            )
        # Now create a customized class for all the motors given
        new_cls = type("Table", (cls,), comps)
        return object.__new__(new_cls)

    def __init__(
        self,
        prefix,
        *args,
        vertical_motor: str = "",
        horizontal_motor: str = "",
        upstream_motor: str = "",
        downstream_motor: str = "",
        **kwargs,
    ):
        # Add a suffix for the tables transform records
        self.transform_prefix = f"{prefix.strip(':')}_trans"
        # Remove the last part of the prefix to get the prefix for the motors
        self.motor_prefix = ":".join(prefix.strip(":").split(":")[:-1])
        if self.motor_prefix == "":
            msg = f"*prefix* argument to {type(self)} is expected "
            msg += f"to include the pseudo motors' path. "
            msg += f"E.g. '255idcVME:table_us:'. Received '{prefix}'."
            raise ValueError(msg)
        # Save all the motor record names
        self._vertical_motor = vertical_motor
        self._horizontal_motor = horizontal_motor
        self._upstream_motor = upstream_motor
        self._downstream_motor = downstream_motor
        # Create the table as normal
        super().__init__(prefix, *args, **kwargs)



def load_table_coros(config=None):
    if config is None:
        config = load_config()
    # Create two-bounce KB mirror sets
    for name, tbl_config in config.get("table", {}).items():
        # Build the motor prefixes
        try:
            prefix = tbl_config["prefix"]
            motor_names = ["upstream_motor", "downstream_motor",
                           "horizontal_motor", "vertical_motor"]
            motors = {attr: tbl_config.get(attr, "") for attr in motor_names}
            
        except KeyError as ex:
            raise exceptions.UnknownDeviceConfiguration(
                f"Device {name} missing '{ex.args[0]}': {tbl_config}"
            ) from ex
        # Make the device
        yield make_device(
            Table, prefix=prefix, name=name, labels={"tables"}, **motors,
        )



def load_tables(config=None):
    asyncio.run(aload_devices(*load_table_coros(config=config)))


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
