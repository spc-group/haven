from ophyd import Device, Component as Cpt, FormattedComponent as FCpt, Kind
from apstools.synApps import TransformRecord

from .motor import HavenMotor


class Table(Device):
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
