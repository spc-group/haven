from unittest.mock import MagicMock
import datetime as dt
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
import time_machine
from tiled.adapters.mapping import MapAdapter
from tiled.adapters.xarray import DatasetAdapter
from tiled.client import Context, from_context
from tiled.server.app import build_app

from haven.instrument import Motor
from haven.catalog import Catalog
from haven import (
    get_motor_position,
    list_current_motor_positions,
    list_motor_positions,
    recall_motor_position,
    save_motor_position,
)

log = logging.getLogger(__name__)

# Metadata from real scan
# {'start': {'EPICS_CA_MAX_ARRAY_BYTES': '16777216',
#            'EPICS_HOST_ARCH': 'rhel8-x86_64',
#            'beamline_id': '25-ID-C (Dev)',
#            'detectors': ['sim_motor_2'],
#            'epics_libca': '/home/beams0/S25IDCUSER/micromamba/envs/haven-dev/lib/python3.10/site-packages/epicscorelibs/lib/libca.so.7.0.7.99.0',
#            'facility_id': 'Advanced Photon Source',
#            'hints': {'dimensions': [[['time'], 'primary']]},
#            'login_id': 's25idcuser@microprobe.xray.aps.anl.gov',
#            'num_intervals': 0,
#            'num_points': 1,
#            'parameters': '',
#            'pid': 2700346,
#            'plan_args': {'delay': None,
#                          'detectors': ['<haven.instrument.motor.Motor object '
#                                        'at 0x7f9c831ca650>'],
#                          'num': 1},
#            'plan_name': 'save_motor_position',
#            'plan_type': 'generator',
#            'position_name': 'test',
#            'purpose': 'testing save motor positions',
#            'sample_name': '',
#            'scan_id': 2,
#            'time': 1725897133.9880543,
#            'uid': 'e4a6d3d1-6543-4a42-98a7-a311af23f4cd',
#            'versions': {'apstools': '1.6.20',
#                         'bluesky': '1.13.0a4',
#                         'databroker': '1.2.5',
#                         'epics': '3.5.6',
#                         'epics_ca': '3.5.6',
#                         'h5py': '3.11.0',
#                         'haven': '2024.8.2',
#                         'matplotlib': '3.9.1.post1',
#                         'numpy': '1.26.4',
#                         'ophyd': '1.9.0',
#                         'pymongo': '4.8.0'},
#            'xray_source': 'undulator: ID25ds:'},
#  'stop': {'exit_status': 'success',
#           'num_events': {'primary': 1},
#           'reason': '',
#           'run_start': 'e4a6d3d1-6543-4a42-98a7-a311af23f4cd',
#           'time': 1725897134.0116587,
#           'uid': 'b6a2cf81-0328-489f-bfcc-967af6207e1b'},
#  'summary': {'datetime': datetime.datetime(2024, 9, 9, 15, 52, 13, 988054, tzinfo=datetime.timezone.utc),
#              'duration': 0.023604393005371094,
#              'plan_name': 'save_motor_position',
#              'scan_id': 2,
#              'stream_names': ['primary'],
#              'timestamp': 1725897133.9880543,
#              'uid': 'e4a6d3d1-6543-4a42-98a7-a311af23f4cd'}}

## Primary stream metadata

# {'descriptors': [{'configuration': {'sim_motor_2': {'data': {'sim_motor_2-description': 'sim_motor_2',
#                                                              'sim_motor_2-motor_egu': 'degrees',
#                                                              'sim_motor_2-velocity': 1.0},
#                                                     'data_keys': {'sim_motor_2-description': {'dtype': 'string',
#                                                                                               'dtype_numpy': '|S40',
#                                                                                               'limits': {'alarm': {'high': None,
#                                                                                                                    'low': None},
#                                                                                                          'control': {'high': None,
#                                                                                                                      'low': None},
#                                                                                                          'display': {'high': None,
#                                                                                                                      'low': None},
#                                                                                                          'warning': {'high': None,
#                                                                                                                      'low': None}},
#                                                                                               'shape': [],
#                                                                                               'source': 'ca://25idc:simMotor:m2.DESC'},
#                                                                   'sim_motor_2-motor_egu': {'dtype': 'string',
#                                                                                             'dtype_numpy': '|S40',
#                                                                                             'limits': {'alarm': {'high': None,
#                                                                                                                  'low': None},
#                                                                                                        'control': {'high': None,
#                                                                                                                    'low': None},
#                                                                                                        'display': {'high': None,
#                                                                                                                    'low': None},
#                                                                                                        'warning': {'high': None,
#                                                                                                                    'low': None}},
#                                                                                             'shape': [],
#                                                                                             'source': 'ca://25idc:simMotor:m2.EGU'},
#                                                                   'sim_motor_2-velocity': {'dtype': 'number',
#                                                                                            'dtype_numpy': '<f8',
#                                                                                            'limits': {'alarm': {'high': None,
#                                                                                                                 'low': None},
#                                                                                                       'control': {'high': 200.0,
#                                                                                                                   'low': 0.1},
#                                                                                                       'display': {'high': 200.0,
#                                                                                                                   'low': 0.1},
#                                                                                                       'warning': {'high': None,
#                                                                                                                   'low': None}},
#                                                                                            'precision': 5,
#                                                                                            'shape': [],
#                                                                                            'source': 'ca://25idc:simMotor:m2.VELO',
#                                                                                            'units': 'degrees'}},
#                                                     'timestamps': {'sim_motor_2-description': 1725483808.090941,
#                                                                    'sim_motor_2-motor_egu': 1725483808.090941,
#                                                                    'sim_motor_2-velocity': 1725483808.090941}}},
#                   'data_keys': {'sim_motor_2': {'dtype': 'number',
#                                                 'dtype_numpy': '<f8',
#                                                 'limits': {'alarm': {'high': None,
#                                                                      'low': None},
#                                                            'control': {'high': 32000.0,
#                                                                        'low': -32000.0},
#                                                            'display': {'high': 32000.0,
#                                                                        'low': -32000.0},
#                                                            'warning': {'high': None,
#                                                                        'low': None}},
#                                                 'object_name': 'sim_motor_2',
#                                                 'precision': 5,
#                                                 'shape': [],
#                                                 'source': 'ca://25idc:simMotor:m2.RBV',
#                                                 'units': 'degrees'}},
#                   'hints': {'sim_motor_2': {'fields': ['sim_motor_2']}},
#                   'name': 'primary',
#                   'object_keys': {'sim_motor_2': ['sim_motor_2']},
#                   'run_start': 'e4a6d3d1-6543-4a42-98a7-a311af23f4cd',
#                   'time': 1725897133.99685,
#                   'uid': 'fcb35152-cb8c-46e8-b923-d07eec666070'}],
#  'stream_name': 'primary'}


# Config data from above run
# In [48]: run['primary/config/sim_motor_2'].read().compute()
# Out[48]: 
# <xarray.Dataset> Size: 24B
# Dimensions:                  (time: 1)
# Dimensions without coordinates: time
# Data variables:
#     sim_motor_2-description  (time) object 8B 'sim_motor_2'
#     sim_motor_2-motor_egu    (time) object 8B 'degrees'
#     sim_motor_2-velocity     (time) float64 8B 1.0


position_runs = {
    "a9b3e0fa-eba1-43e0-a38c-c7ac76278000": MapAdapter(
        {
            "primary": MapAdapter(
                {
                    "data": DatasetAdapter.from_dataset(pd.DataFrame({
                        "motorA": [12.0],
                        "motorB": [-113.25],
                    }).to_xarray()),
                },
                metadata={
                    "descriptors": {
                        "data_keys": {
                            "motorA": {
                                "object_name": "motorA"
                            },
                            "motorB": {
                                "object_name": "motorB"
                            },
                        },
                    },
                }
            ),
        },
        metadata={
            "start": {
                'plan_name': 'save_motor_position',
                "position_name": "Good position A",
                'time': 1725897133.9880543,
                'uid': "a9b3e0fa-eba1-43e0-a38c-c7ac76278000",
            },
        },
    ),
    "1b7f2ef5-6a3c-496e-9f6f-f1a4805c0065": MapAdapter({}),
}


@pytest.fixture()
def client(mocker):
    tree = MapAdapter(position_runs)
    app = build_app(tree)
    with Context.from_app(app) as context:
        client = from_context(context)
        mocker.patch("haven.motor_position.tiled_client",
                     MagicMock(return_value=client))
        yield client


@pytest.fixture
def motors(sim_registry):
    # Create the motors
    motors = [
        Motor("", name="motor_B"),
        Motor("", name="motor_A"),
    ]
    for motor in motors:
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


async def test_get_motor_position_by_uid(client):
    uid = "a9b3e0fa-eba1-43e0-a38c-c7ac76278000"
    result = get_motor_position(uid=uid)
    assert result.name == "Good position A"
    assert result.motors[0].name == "motorA"
    assert result.motors[0].readback == 12.0


def test_recall_motor_position(mongodb, sim_motor_registry):
    # Re-set the previous value
    uid = str(mongodb.motor_positions.find_one({"name": "Good position A"})["_id"])
    plan = recall_motor_position(uid=uid, collection=mongodb.motor_positions)
    messages = list(plan)
    # Check the plan output
    msg0 = messages[0]
    assert msg0.obj.name == "SLT V Upper"
    assert msg0.args[0] == 510.5
    msg1 = messages[1]
    assert msg1.obj.name == "SLT V Lower"
    assert msg1.args[0] == -211.93


def test_list_motor_positions(mongodb, capsys):
    # Do the listing
    list_motor_positions(collection=mongodb.motor_positions)
    # Check stdout for printed motor positions
    captured = capsys.readouterr()
    assert len(captured.out) > 0
    uid = str(mongodb.motor_positions.find_one({"name": "Good position A"})["_id"])
    timestamp = "2022-08-19 19:10:51"
    expected = (
        f'\n\033[1mGood position A\033[0m (uid="{uid}", timestamp={timestamp})\n'
        "┣━SLT V Upper: 510.5, offset: 0.0\n"
        "┗━SLT V Lower: -211.93, offset: None\n"
    )
    assert captured.out == expected


def test_motor_position_e2e(mongodb, sim_motor_registry):
    """Check that a motor position can be saved, then recalled using
    a simulated motor.

    """
    # Create an epics motor for setting values manually
    motor1 = sim_motor_registry.find(name="SLT V Upper")
    # Set a fake value
    motor1.set(504.6).wait(timeout=2)
    # assert epics.caget(pv, use_monitor=False) == 504.6
    # time.sleep(0.1)
    assert motor1.get().readback == 504.6
    # Save motor position
    uid = save_motor_position(
        motor1,
        name="starting point",
        collection=mongodb.motor_positions,
    )
    # Change to a different value
    motor1.set(520).wait(timeout=2)
    assert motor1.get().readback == 520
    # Recall the saved position and see if it complies
    plan = recall_motor_position(uid=uid, collection=mongodb.motor_positions)
    msg = next(plan)
    assert msg.obj.name == "SLT V Upper"
    assert msg.args[0] == 504.6


def test_list_current_motor_positions(mongodb, capsys):
    # Get our simulated motors into the device registry
    with capsys.disabled():
        motorA = FakeHavenMotor(name="Motor A")
        motorB = FakeHavenMotor(name="Motor B")
        motorA.wait_for_connection()
        motorB.wait_for_connection()
        # Move to some other motor position so we can tell it saved the right one
        motorA.set(11.0).wait()
        motorA.user_offset.set(1.5).wait()
        motorB.set(23.0).wait()
    # List the current motor position
    list_current_motor_positions(motorA, motorB, name="Current motor positions")
    # Check stdout for printed motor positions
    captured = capsys.readouterr()
    assert len(captured.out) > 0
    timestamp = fake_time.strftime("%Y-%m-%d %H:%M:%S")
    timestamp = "2022-08-19 19:10:51"
    expected = (
        f"\n\033[1mCurrent motor positions\033[0m (timestamp={timestamp})\n"
        "┣━Motor A: 11.0, offset: 1.5\n"
        "┗━Motor B: 23.0, offset: 0.0\n"
    )
    assert captured.out == expected


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
