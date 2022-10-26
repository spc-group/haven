import asyncio
from typing import Optional, Sequence

from pydantic import BaseModel
import pymongo


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
        print(dir(collection))
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
    # Prepare the motor positions
    motor_axes = [MotorAxis(name=m.name, readback=m.get().readback) for m in motors]
    position = MotorPosition(name=name, motors=motor_axes)
    # Write to the database
    pos_id = position.save(collection=collection)
    return pos_id
