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
    uid: Optional[str] = None

    def save(self, collection):
        payload = {"name": self.name, "motors": [m.as_dict() for m in self.motors]}
        item_id = collection.insert_one(payload).inserted_id
        return item_id

    @classmethod
    def load(Cls, document):
        # Create a MotorPosition object
        motor_axes = [
            MotorAxis(name=m["name"], readback=m["readback"]) for m in document["motors"]
        ]
        position = Cls(name=document["name"], motors=motor_axes, uid=str(document["_id"]))
        return position


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
            return motor_data

    motor_axes = [MotorAxis(name=m.name, readback=rbv(m)) for m in motors]
    position = MotorPosition(name=name, motors=motor_axes)
    # Write to the database
    pos_id = position.save(collection=collection)
    log.info(f"Saved motor position {name} (uid={pos_id})")
    return pos_id


def list_motor_positions(collection=None):
    results = collection.find()
    for doc in results:
        position = MotorPosition.load(doc)
        output = f'"\n{position.name}" (uid="{position.uid}")\n'
        for idx, motor in enumerate(position.motors):
            # Figure out some nice tree aesthetics
            is_last_motor = idx == (len(position.motors) - 1)
            box_char = "┗" if is_last_motor else "┣"
            output += f'{box_char}━"{motor.name}": {motor.readback}\n'
        print(output, end="")


def get_motor_position(uid: Optional[str] = None, name: Optional[str] = None, collection=None):
    """Retrieve a previously saved motor position from the database."""
    # Check that at least one of the parameters is given
    has_query_param = any([val is not None for val in [uid, name]])
    if not has_query_param:
        raise TypeError("At least one query parameter (*uid*, *name*) is required")
    # Build query for finding motor positions
    query_params = {"_id": uid,
                    "name": name}
    # Filter out query parameters that are ``None``
    query_params = {k: v for k, v in query_params.items() if v is not None}
    result = collection.find_one(query_params)
    # Feedback for if no matching motor positions are in the database
    if result is None:
        raise exceptions.DocumentNotFound(
            f'Could not find document matching: _id="{uid}", name="{name}"'
        )
    position = MotorPosition.load(result)
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
