import asyncio
from typing import Optional, Sequence
import logging

from pydantic import BaseModel
import pymongo
from bluesky import plans as bp, plan_stubs as bps
from ophyd import EpicsMotor

from .instrument.instrument_registry import registry
from . import exceptions


log = logging.getLogger(__name__)


class MotorAxis(BaseModel):
    name: str
    readback: float

    def as_dict(self):
        return {"name": self.name, "readback": self.readback}


class MotorPosition(BaseModel):
    name: str
    motors: Sequence[MotorAxis]

    def save(self, collection):
        payload = {"name": self.name, "motors": [m.as_dict() for m in self.motors]}
        item_id = collection.insert_one(payload).inserted_id
        return item_id


def save_motor_position(*motors, name: str, collection=None):
    """Save the current positions of a number of motors to a database.

    Parameters
    ==========
    *motors
      The list of motors (or motor names/labels) whose position to
      save.
    name
      A human-readable name for this position (e.g. "sample center")
    collection
      A pymongo collection object to receive the data. Meant for
      testing.

    Returns
    =======
    item_id
      The ID of the item in the database.
    """
    # Resolve device names or labels
    motors = [registry.find(name=m) for m in motors]
    # Prepare the motor positions
    def rbv(motor):
        """Helper function to get readback value (rbv)."""
        motor_data = motor.get()
        if hasattr(motor_data, "readback"):
            return motor_data.readback
        elif hasattr(motor_data, "user_readback"):
            return motor_data.user_readback
        else:
            raise ValueError("Could not find readback value.")

    motor_axes = [MotorAxis(name=m.name, readback=rbv(m)) for m in motors]
    position = MotorPosition(name=name, motors=motor_axes)
    # Write to the database
    pos_id = position.save(collection=collection)
    log.info(f"Saved motor position {name} (uid={pos_id})")
    return pos_id


def get_motor_position(uid, collection=None):
    """Retrieve a previously saved motor position from the database."""
    result = collection.find_one({"_id": uid})
    if result is None:
        raise exceptions.DocumentNotFound(
            f"Could not find document matching: _id={uid}"
        )
    # Create a MotorPosition object
    motor_axes = [
        MotorAxis(name=m["name"], readback=m["readback"]) for m in result["motors"]
    ]
    position = MotorPosition(name=result["name"], motors=motor_axes)
    return position


def recall_motor_position(uid, collection=None):
    # Get the saved position from the database
    position = get_motor_position(uid=uid, collection=collection)
    # Create a move plan to recall the position
    plan_args = []
    for axis in position.motors:
        motor = registry.find(name=axis.name)
        plan_args.append(motor)
        plan_args.append(axis.readback)
    yield from bps.mv(*plan_args)
