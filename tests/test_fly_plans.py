from unittest.mock import MagicMock
from collections import OrderedDict

from ophyd import sim
import numpy as np

from haven.plans.fly import fly_scan, grid_fly_scan, FlyerCollector


def test_set_fly_params(sim_aerotech_flyer):
    """Does the plan set the parameters of the flyer motor."""
    flyer = sim_aerotech_flyer
    # step size == 10
    plan = fly_scan(
        detectors=[], flyer=flyer, start=-20, stop=30, num=6, dwell_time=0.15
    )
    messages = list(plan)
    open_msg = messages[0]
    param_msgs = messages[1:7]
    fly_msgs = messages[9:-1]
    close_msg = messages[:-1]
    print([m.command for m in messages])
    assert param_msgs[0].command == "set"
    assert param_msgs[1].command == "wait"
    assert param_msgs[2].command == "set"
    assert param_msgs[3].command == "wait"
    assert param_msgs[4].command == "set"
    # Make sure the step size is calculated properly
    new_step_size = param_msgs[4].args[0]
    assert new_step_size == 10


def test_collector_describe():
    aerotech = MagicMock()
    aerotech.describe_collect.return_value = {
        "positions": OrderedDict(
            [
                (
                    "aerotech_horiz",
                    {
                        "source": "PV:25idc:m1.RBV",
                        "dtype": "number",
                        "shape": [],
                        "units": "micron",
                        "lower_ctrl_limit": -28135.352,
                        "upper_ctrl_limit": 31864.648,
                        "precision": 7,
                    },
                ),
                (
                    "aerotech_horiz_user_setpoint",
                    {
                        "source": "PV:25idc:m1.VAL",
                        "dtype": "number",
                        "shape": [],
                        "units": "micron",
                        "lower_ctrl_limit": -28135.352,
                        "upper_ctrl_limit": 31864.648,
                        "precision": 7,
                    },
                ),
            ]
        )
    }
    I0 = MagicMock()
    I0.describe_collect.return_value = {
        "I0": OrderedDict(
            [
                (
                    "I0_net_counts",
                    {
                        "source": "PV:25idcVME:3820:scaler1_netA.D",
                        "dtype": "number",
                        "shape": [],
                        "units": "",
                        "lower_ctrl_limit": 0.0,
                        "upper_ctrl_limit": 0.0,
                        "precision": 0,
                    },
                )
            ]
        )
    }
    flyers = [aerotech, I0]
    collector = FlyerCollector(flyers, stream_name="primary")
    desc = collector.describe_collect()
    assert "primary" in desc.keys()
    assert list(desc["primary"].keys()) == [
        "aerotech_horiz",
        "aerotech_horiz_user_setpoint",
        "I0_net_counts",
    ]
    assert (
        desc["primary"]["aerotech_horiz"]
        == aerotech.describe_collect()["positions"]["aerotech_horiz"]
    )


def test_collector_collect():
    aerotech = MagicMock()
    aerotech.collect.return_value = [
        {
            "data": {
                "aerotech_horiz": -1000.0,
                "aerotech_horiz_user_setpoint": -1000.0,
            },
            "timestamps": {
                "aerotech_horiz": 1691957265.6073308,
                "aerotech_horiz_user_setpoint": 1691957265.6073308,
            },
            "time": 1691957265.6073308,
        },
        {
            "data": {"aerotech_horiz": -800.0, "aerotech_horiz_user_setpoint": -800.0},
            "timestamps": {
                "aerotech_horiz": 1691957266.1137164,
                "aerotech_horiz_user_setpoint": 1691957266.1137164,
            },
            "time": 1691957266.1137164,
        },
    ]
    I0 = MagicMock()
    I0.collect.return_value = [
        {
            "data": {"I0_net_counts": [0]},
            "timestamps": {"I0_net_counts": [1691957269.1575842]},
            "time": 1691957269.1575842,
        },
        {
            "data": {"I0_net_counts": [0]},
            "timestamps": {"I0_net_counts": [1691957269.0734286]},
            "time": 1691957269.0734286,
        },
    ]
    flyers = [aerotech, I0]
    collector = FlyerCollector(flyers, stream_name="primary")
    events = list(collector.collect())
    expected_events = [
        {
            "data": {
                "I0_net_counts": [0],
                "aerotech_horiz": -1000.0,
                "aerotech_horiz_user_setpoint": -1000.0,
            },
            "timestamps": {
                "I0_net_counts": [1691957269.1575842],
                "aerotech_horiz": 1691957265.6073308,
                "aerotech_horiz_user_setpoint": 1691957265.6073308,
            },
            "time": 1691957265.6073308,
        },
        {
            "data": {
                "I0_net_counts": [0],
                "aerotech_horiz": -800.0,
                "aerotech_horiz_user_setpoint": -800.0,
            },
            "timestamps": {
                "I0_net_counts": [1691957269.0734286],
                "aerotech_horiz": 1691957266.1137164,
                "aerotech_horiz_user_setpoint": 1691957266.1137164,
            },
            "time": 1691957266.1137164,
        },
    ]
    assert len(events) == 2
    assert events == expected_events


def test_fly_grid_scan(sim_aerotech_flyer):
    flyer = sim_aerotech_flyer
    stepper = sim.motor
    # step size == 10
    plan = grid_fly_scan([], stepper, -100, 100, 11, flyer, -20, 30, 6, snake_axes=[flyer])
    messages = list(plan)
    # from pprint import pprint
    for msg in messages:
        print(f"{msg.command:<10}\t{getattr(msg.obj, 'name', 'None'):<20}\t{msg.args}")
    assert messages[0].command == "stage"
    assert messages[1].command == "open_run"
    # Check that we move the stepper first
    assert messages[2].command == "checkpoint"
    assert messages[3].command == "set"
    assert messages[3].args == (-100,)
    assert messages[4].command == "wait"
    # Check that flyer motor positions snake back and forth
    stepper_positions = [
        msg.args[0]
        for msg in messages
        if (msg.command == "set" and msg.obj.name == "motor")
    ]
    flyer_start_positions = [
        msg.args[0]
        for msg in messages
        if (msg.command == "set" and msg.obj.name == "flyer_start_position")
    ]
    flyer_end_positions = [
        msg.args[0]
        for msg in messages
        if (msg.command == "set" and msg.obj.name == "flyer_end_position")
    ]    
    assert stepper_positions == list(np.linspace(-100, 100, num=11))
    assert flyer_start_positions == [-20, 30, -20, 30, -20, 30, -20, 30, -20, 30, -20]
    assert flyer_end_positions == [30, -20, 30, -20, 30, -20, 30, -20, 30, -20, 30]
