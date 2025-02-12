import datetime as dt
import logging
from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
import time_machine
from ophyd_async.testing import set_mock_value
from tiled.adapters.mapping import MapAdapter
from tiled.adapters.table import TableAdapter
from tiled.adapters.xarray import DatasetAdapter
from tiled.client import Context, from_context
from tiled.server.app import build_app

from haven.devices import Motor
from haven.motor_position import (
    get_motor_position,
    get_motor_positions,
    list_current_motor_positions,
    list_motor_positions,
    recall_motor_position,
    save_motor_position,
)

log = logging.getLogger(__name__)

# Use a timezone we're not likely to be in for testing tz-aware behavior
fake_time = dt.datetime(2022, 8, 19, 19, 10, 51, tzinfo=ZoneInfo("Asia/Taipei"))


position_runs = {
    "a9b3e0fa-eba1-43e0-a38c-c7ac76278000": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "internal": MapAdapter(
                        {
                            "events": TableAdapter.from_pandas(
                                pd.DataFrame(
                                    {
                                        "motor_A": [12.0],
                                        "motor_B": [-113.25],
                                    }
                                )
                            ),
                        }
                    ),
                },
                metadata={
                    "data_keys": {
                        "motor_A": {"object_name": "motor_A"},
                        "motor_B": {"object_name": "motor_B"},
                    },
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "Good position A",
            "time": 1725897133,
            "uid": "a9b3e0fa-eba1-43e0-a38c-c7ac76278000",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Good position A",
                "time": 1725897133,
                "uid": "a9b3e0fa-eba1-43e0-a38c-c7ac76278000",
            },
        },
    ),
    # A second saved motor position
    "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0065": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "internal": MapAdapter(
                        {
                            "events": TableAdapter.from_pandas(
                                pd.DataFrame(
                                    {
                                        "motorC": [11250.0],
                                    }
                                )
                            ),
                        }
                    ),
                },
                metadata={
                    "data_keys": {
                        "motorC": {"object_name": "motorC"},
                    },
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "A good position B",
            "time": 1725897193,
            "uid": "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0065",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "A good position B",
                "time": 1725897193,
                "uid": "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0065",
            },
        },
    ),
    # A saved motor position, but older
    "5dd9a185-d5c4-4c8b-a719-9d7beb9007dc": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(
                        pd.DataFrame(
                            {
                                "motorC": [11250.0],
                            }
                        ).to_xarray()
                    ),
                },
                metadata={
                    "data_keys": {
                        "motorC": {"object_name": "motorC"},
                    },
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "Good position C",
            "time": 1725897033,
            "uid": "5dd9a185-d5c4-4c8b-a719-9d7beb9007dc",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Good position C",
                "time": 1725897033,
                "uid": "5dd9a185-d5c4-4c8b-a719-9d7beb9007dc",
            },
        },
    ),
    # A saved motor position, but older
    "42b8c45d-e98d-4f59-9ce8-8f14134c90bd": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(
                        pd.DataFrame(
                            {
                                "motorC": [11250.0],
                            }
                        ).to_xarray()
                    ),
                },
                metadata={
                    "data_keys": {
                        "motorC": {"object_name": "motorC"},
                    },
                },
            ),
        },
        metadata={
            "plan_name": "save_motor_position",
            "position_name": "Another good position",
            "time": 1725897233,
            "uid": "42b8c45d-e98d-4f59-9ce8-8f14134c90bd",
            "start": {
                "plan_name": "save_motor_position",
                "position_name": "Another good position",
                "time": 17258972333,
                "uid": "42b8c45d-e98d-4f59-9ce8-8f14134c90bd",
            },
        },
    ),
    # A scan that's not a saved motor position
    "9bcd07e9-3188-49d3-a1ce-e3b51ebe48b5": MapAdapter(
        {},
        metadata={
            "plan_name": "xafs_scan",
            "time": 1725897133,
        },
    ),
}


@pytest.fixture()
def client(mocker):
    tree = MapAdapter(position_runs)
    app = build_app(tree)
    with Context.from_app(app) as context:
        client = from_context(context)
        mocker.patch(
            "haven.motor_position.tiled_client", MagicMock(return_value=client)
        )
        yield client


@pytest.fixture
async def motors(sim_registry):
    # Create the motors
    motors = [
        Motor("", name="motor_A"),
        Motor("", name="motor_B"),
    ]
    for motor in motors:
        await motor.connect(mock=True)
        sim_registry.register(motor)
    return motors


def test_save_motor_position_by_device(motors):
    # Move to some other motor position so we can tell it saved the right one
    motorA, motorB = motors
    # Save the current motor position
    plan = save_motor_position(motorA, motorB, name="Sample center")
    # Check that the right read messages get emitted
    messages = list(plan)
    # Check that the motors got saved
    readA, readB = messages[6:8]
    assert readA.obj is motorA
    assert readB.obj is motorB


def test_save_motor_position_by_name(motors):
    # Check that no entry exists before saving it
    motorA, motorB = motors
    # Save the current motor position
    plan = save_motor_position(motorA.name, motorB.name, name="Sample center")
    # Check that the motors got saved
    # Check that the right read messages get emitted
    messages = list(plan)
    # Check that the motors got saved
    readA, readB = messages[6:8]
    assert readA.obj is motorA
    assert readB.obj is motorB


def test_get_motor_position(client):
    uid = "a9b3e0fa-eba1-43e0-a38c-c7ac76278000"
    result = get_motor_position(uid=uid)
    assert result.name == "Good position A"
    assert result.motors[0].name == "motor_A"
    assert result.motors[0].readback == 12.0


async def test_get_motor_positions(client):
    results = get_motor_positions(after=1725897100, before=1725897200)
    results = [pos async for pos in results]
    assert len(results) == 2
    # Check the motor position details
    motorA, motorB = results
    assert motorA.uid == "a9b3e0fa-eba1-43e0-a38c-c7ac76278000"


async def test_get_motor_positions_by_name(client):
    results = get_motor_positions(name=r"^.*good.+itio.+[AB]$", case_sensitive=False)
    results = [pos async for pos in results]
    assert len(results) == 2
    # Check the motor position details
    motorA, motorB = results
    assert motorA.uid == "a9b3e0fa-eba1-43e0-a38c-c7ac76278000"


def test_recall_motor_position(client, motors):
    # Re-set the previous value
    uid = "a9b3e0fa-eba1-43e0-a38c-c7ac76278000"
    plan = recall_motor_position(uid=uid)
    messages = list(plan)
    # Check the plan output
    msg0 = messages[0]
    assert msg0.obj.name == "motor_A"
    assert msg0.args[0] == 12.0
    msg1 = messages[1]
    assert msg1.obj.name == "motor_B"
    assert msg1.args[0] == -113.25


@time_machine.travel(fake_time, tick=True)
async def test_list_motor_positions(client, capsys):
    # Do the listing
    await list_motor_positions()
    # Check stdout for printed motor positions
    captured = capsys.readouterr()
    assert len(captured.out) > 0
    first_motor = captured.out.split("\n\n")[0]
    uid = "a9b3e0fa-eba1-43e0-a38c-c7ac76278000"
    timestamp = "2024-09-09 23:52:13"
    expected = "\n".join(
        [
            f"Good position A",
            f'┃ uid="{uid}", {timestamp}',
            f"┣━motor_A: 12.0, offset: None",
            f"┗━motor_B: -113.25, offset: None",
        ]
    )
    print(first_motor)
    print("===")
    print(expected)
    assert first_motor == expected


@time_machine.travel(fake_time, tick=True)
async def test_list_current_motor_positions(motors, capsys):
    # Get our simulated motors into the device registry
    motorA, motorB = motors
    with capsys.disabled():
        # Move to some other motor position so we can tell it saved the right one
        set_mock_value(motorA.user_readback, 11.0)
        set_mock_value(motorA.user_offset, 1.5)
        set_mock_value(motorB.user_readback, 23.0)
    # List the current motor position
    await list_current_motor_positions(motorA, motorB, name="Current motor positions")
    # Check stdout for printed motor positions
    captured = capsys.readouterr()
    assert len(captured.out) > 0
    timestamp = "2022-08-19 19:10:51"
    expected = "\n".join(
        [
            f"Current motor positions",
            f"┃ {timestamp}",
            f"┣━motor_A: 11.0, offset: 1.5",
            f"┗━motor_B: 23.0, offset: 0.0",
        ]
    )
    assert captured.out.strip("\n") == expected.strip("\n")


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
