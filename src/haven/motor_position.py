import logging
import time
from datetime import datetime
from typing import Sequence, Mapping
from collections import ChainMap

import intake
import pymongo
from bluesky import plan_stubs as bps, plans as bp
from bson.objectid import ObjectId
from pydantic import BaseModel

from . import exceptions
from .instrument.instrument_registry import registry
from .catalog import tiled_client

log = logging.getLogger(__name__)


__all__ = [
    "save_motor_position",
    "list_motor_positions",
    "recall_motor_position",
    "list_current_motor_positions",
]


class MotorAxis(BaseModel):
    name: str
    readback: float
    offset: float | None = None

    def as_dict(self):
        return {"name": self.name, "readback": self.readback, "offset": self.offset}


class MotorPosition(BaseModel):
    name: str
    motors: Sequence[MotorAxis]
    uid: str | None = None
    savetime: float | None = None

    @classmethod
    def load(Cls, run):
        if run.metadata['start']['plan_name'] != "save_motor_position":
            raise ValueError(f"Run {run} is not a motor position.")
        # Extract motor positions from the run
        stream = run['primary']
        data_keys = stream.metadata['descriptors']['data_keys'].values()
        motor_axes = []
        for data_key in data_keys:
            mname = data_key['object_name']
            axis = MotorAxis(
                name=mname,
                readback=stream['data'][mname].read()[0],
            )
            motor_axes.append(axis)
        # Create a MotorPosition object
        position = Cls(
            name=run.metadata['start']['position_name'],
            motors=motor_axes,
            uid=run.metadata['start']['uid'],
            savetime=run.metadata['start']['time'],
        )
        return position


def default_collection():
    catalog = intake.catalog.load_combo_catalog()["haven"]
    client = catalog._asset_registry_db.client
    collection = client.get_database().get_collection("motor_positions")
    return collection


# Prepare the motor positions
def rbv(motor):
    """Helper function to get readback value (rbv)."""
    try:
        # Wrap this in a try block because not every signal has this argument
        motor_data = motor.get(use_monitor=False)
    except TypeError:
        log.debug("Failed to do get() with ``use_monitor=False``")
        motor_data = motor.get()
    if hasattr(motor_data, "readback"):
        return motor_data.readback
    elif hasattr(motor_data, "user_readback"):
        return motor_data.user_readback
    else:
        return motor_data


def save_motor_position(*motors, name: str, md: Mapping = {}):
    """A Bluesky plan to Save the current positions of a number of motors.

    Parameters
    ==========
    *motors
      The list of motors (or motor names/labels) whose position to
      save.
    name
      A human-readable name for this position (e.g. "sample center")
    md
      Additional metadata to store with the motor position.

    """
    # Resolve device names or labels
    motors = registry.findall(motors)
    # Create the new run object
    _md = {
        'position_name': name,
        'plan_name': "save_motor_position",
    }
    _md.update(md)
    yield from bp.count(motors, md=_md)


def print_motor_position(position):
    BOLD = "\033[1m"
    END = "\033[0m"
    # Prepare metadata strings for the header
    metadata = []
    if position.uid is not None:
        metadata.append(f'uid="{position.uid}"')
    if position.savetime is not None:
        timestamp = datetime.fromtimestamp(position.savetime).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        ts_str = f"timestamp={timestamp}"
        metadata.append(ts_str)
    if len(metadata) > 0:
        metadata_str = f" ({', '.join(metadata)})"
    else:
        metadata_str = ""
    # Write the output header
    output = f"\n{BOLD}{position.name}{END}{metadata_str}\n"
    # Write the motor positions
    for idx, motor in enumerate(position.motors):
        # Figure out some nice tree aesthetics
        is_last_motor = idx == (len(position.motors) - 1)
        box_char = "┗" if is_last_motor else "┣"
        output += f"{box_char}━{motor.name}: {motor.readback}, offset: {motor.offset}\n"
    print(output, end="")


def list_motor_positions(collection=None):
    """Print a list of saved motor positions.

    The name and UID will be printed, along with each motor and it's
    position.

    Parameters
    ==========
    collection
      The mongodb collection from which to print motor positions.

    """
    # Get default collection if none was given
    if collection is None:
        collection = default_collection()
    # Get the motor positions from disk
    results = collection.find()
    # Go through the results and display them
    were_found = False
    for doc in results:
        were_found = True
        position = MotorPosition.load(doc)
        print_motor_position(position)
    # Some feedback in the case of empty motor positions
    if not were_found:
        print(f"No motor positions found: {collection}")


def get_motor_position(
    uid: str
) -> MotorPosition:
    """Retrieve a previously saved motor position from the database.

    Parameters
    ==========
    uid
      The universal identifier for the Bluesky run with motor position
      info.

    Returns
    =======
    position
      The most recent motor position with data retrieved from the
      database.

    """
    # Filter out query parameters that are ``None``
    client = tiled_client()
    run = client[uid]
    # Feedback for if no matching motor positions are in the database
    position = MotorPosition.load(run)
    return position


def recall_motor_position(
    uid: str | None = None, name: str | None = None, collection=None
):
    """Set motors to their previously saved positions.

    Parameters
    ==========
    uid
      The universal identifier for the the document in the collection.
    name
      The name of the saved motor position, as given with the *name*
      parameter to the ``save_motor_position`` function.
    collection
      The mongodb collection from which to print motor positions.

    """
    # Get default collection if none was given
    if collection is None:
        collection = default_collection()
    # Get the saved position from the database
    position = get_motor_position(uid=uid, name=name, collection=collection)
    # Create a move plan to recall the position
    plan_args = []
    for axis in position.motors:
        motor = registry.find(name=axis.name)
        plan_args.append(motor)
        plan_args.append(axis.readback)
    yield from bps.mv(*plan_args)


def list_current_motor_positions(*motors, name="current motor"):
    """list and print the current positions of a number of motors

    Parameters
    ==========
    *motors
      The list of motors (or motor names/labels) whose position to
      save.
    name
      A human-readable name for this position (e.g. "sample center")

    """
    # Resolve device names or labels
    motors = [registry.find(name=m) for m in motors]
    # Build the list of motor positions
    motor_axes = []
    for m in motors:
        payload = dict(name=m.name, readback=rbv(m))
        # Save the calibration offset for motors
        if hasattr(m, "user_offset"):
            payload["offset"] = m.user_offset.get()
        axis = MotorAxis(**payload)
        motor_axes.append(axis)
    position = MotorPosition(
        name=name, motors=motor_axes, uid=None, savetime=time.time()
    )
    # Display the current motor positions
    print_motor_position(position)


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
