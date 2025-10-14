from unittest import mock

import numpy as np
import pytest
from ophyd import sim
from ophyd_async.core import DetectorTrigger, TriggerInfo
from ophyd_async.epics.motor import Motor
from scanspec.core import Path
from scanspec.specs import Line

from haven.devices import DG645Delay, IonChamber, SoftGlueDelay, Xspress3Detector
from haven.plans import fly_scan, grid_fly_scan
from haven.plans._fly import fly_scan_with_spec, fly_segment, prepare_detectors

fly_motor = Motor("255idcVME:m1", name="m1")


@pytest.fixture()
def flyer(sim_registry, mocker):
    m1 = fly_motor
    return m1


def test_fly_segment(flyer):
    xspress = Xspress3Detector("")
    spec = Line(fly_motor, -10, 10, 6)
    trigger_info = TriggerInfo(trigger=DetectorTrigger.EDGE_TRIGGER, number_of_events=6)
    plan = fly_segment([xspress], motors=[flyer], spec=spec, trigger_info=trigger_info)
    msgs = list(plan)
    assert len(msgs) > 2
    # Prepare the scan
    assert msgs[0].command == "prepare"
    assert msgs[1].command == "prepare"
    prepared_objs = {
        msgs[0].obj,
        msgs[1].obj,
    }
    assert prepared_objs == {xspress, flyer}
    assert msgs[2].command == "wait"
    # Start the scan
    assert msgs[3].command == "kickoff"
    assert msgs[3].obj is xspress
    assert msgs[4].command == "wait"
    assert msgs[5].command == "kickoff"
    assert msgs[5].obj is flyer
    assert msgs[6].command == "wait"
    # Finish the scan
    assert msgs[7].command == "complete"
    assert msgs[7].obj is flyer
    assert msgs[8].command == "wait"
    assert msgs[9].command == "complete"
    assert msgs[9].obj is xspress
    assert msgs[10].command == "wait"


def test_line_prepares_flyer_path(flyer):
    """Does the plan set the parameters of the flyer motor?"""
    # step size == 10
    plan = fly_scan_with_spec([], flyer, -20, 30, num=6, dwell_time=1.5)
    messages = list(plan)
    prep_msg = [
        msg for msg in messages if msg.command == "prepare" and msg.obj is flyer
    ][0]
    prep_path = prep_msg.args[0]
    assert isinstance(prep_path, Path)
    points = prep_path.consume()
    print(points)
    np.testing.assert_equal(points.midpoints[flyer], np.linspace(-20, 30, num=6))
    np.testing.assert_equal(points.lower[flyer], np.linspace(-25, 25, num=6))
    np.testing.assert_equal(points.upper[flyer], np.linspace(-15, 35, num=6))
    np.testing.assert_equal(points.duration, np.full(shape=(6,), fill_value=1.5))


def test_line_prepares_controller_path(flyer):
    """Does the plan set the parameters of the flyer controller?"""
    controller = SoftGlueDelay(prefix="spam_eggs:", name="soft_glue_delay")
    plan = fly_scan_with_spec(
        [], flyer, -20, 30, num=6, dwell_time=1.5, flyer_controllers=[controller]
    )
    messages = list(plan)
    from pprint import pprint

    pprint(messages)
    prep_msg = [
        msg for msg in messages if msg.command == "prepare" and msg.obj is controller
    ][0]
    prep_path = prep_msg.args[0]
    assert isinstance(prep_path, Path)
    points = prep_path.consume()
    print(points)
    np.testing.assert_equal(points.midpoints[flyer], np.linspace(-20, 30, num=6))
    np.testing.assert_equal(points.lower[flyer], np.linspace(-25, 25, num=6))
    np.testing.assert_equal(points.upper[flyer], np.linspace(-15, 35, num=6))
    np.testing.assert_equal(points.duration, np.full(shape=(6,), fill_value=1.5))


def test_fly_scan_metadata(flyer, ion_chamber):
    """Does the plan set the parameters of the flyer motor."""
    md = {"spam": "eggs"}
    plan = fly_scan_with_spec([ion_chamber], flyer, -20, 30, num=6, dwell_time=1, md=md)
    messages = list(plan)
    assert messages[0].command == "stage"
    assert messages[1].command == "stage"
    open_msg = messages[2]
    assert open_msg.command == "open_run"
    real_md = open_msg.kwargs
    expected_md = {
        "plan_args": {
            "detectors": list([repr(ion_chamber)]),
            "num": 6,
            "dwell_time": 1,
            "flyer_controllers": [],
            "trigger": "DetectorTrigger.INTERNAL",
            "*args": (repr(flyer), -20, 30),
        },
        "plan_name": "fly_scan",
        "motors": [flyer.name],
        "detectors": [ion_chamber.name],
        "spam": "eggs",
    }
    assert real_md == expected_md


# Old tests are below this line
# -----------------------------


def test_set_fly_motor_params_old(flyer):
    """Does the plan set the parameters of the flyer motor?"""
    # step size == 10
    plan = fly_scan([], flyer, -20, 30, num=6, dwell_time=1.5)
    messages = list(plan)
    prep_msg = [
        msg for msg in messages if msg.command == "prepare" and msg.obj is flyer
    ][0]
    prep_info = prep_msg.args[0]
    assert prep_info.start_position == -20
    assert prep_info.end_position == 30
    assert prep_info.time_for_move == 9.0
    assert prep_info.point_count == 6


def test_set_fly_params_reverse_old(flyer):
    """Does the plan set the parameters of the flyer motor when going
    higher to lower positions?

    """
    plan = fly_scan([], flyer, 20, -30, num=6, dwell_time=1.5)
    messages = list(plan)
    prep_msg = [
        msg for msg in messages if msg.command == "prepare" and msg.obj is flyer
    ][0]
    prep_info = prep_msg.args[0]
    assert prep_info.start_position == 20
    assert prep_info.end_position == -30
    assert prep_info.time_for_move == 9.0
    assert prep_info.point_count == 6


def test_fly_scan_metadata_old(flyer, ion_chamber):
    """Does the plan set the parameters of the flyer motor."""
    md = {"spam": "eggs"}
    plan = fly_scan([ion_chamber], flyer, -20, 30, num=6, dwell_time=1, md=md)
    messages = list(plan)
    open_msg = messages[2]
    assert open_msg.command == "open_run"
    real_md = open_msg.kwargs
    expected_md = {
        "plan_args": {
            "detectors": list([repr(ion_chamber)]),
            "num": 6,
            "dwell_time": 1,
            "delay_outputs": [],
            "trigger": "DetectorTrigger.INTERNAL",
            "*args": (repr(flyer), -20, 30),
        },
        "plan_name": "fly_scan",
        "motors": [flyer.name],
        "detectors": [ion_chamber.name],
        "spam": "eggs",
    }
    assert real_md == expected_md


def test_fly_grid_scan(flyer):
    stepper = sim.motor
    # step size == 10
    plan = grid_fly_scan(
        [],
        stepper,
        -100,
        100,
        11,
        flyer,
        -20,
        30,
        6,
        dwell_time=1.0,
        snake_axes=[flyer],
    )
    messages = list(plan)
    assert messages[0].command == "stage"
    assert messages[1].command == "open_run"
    assert messages[2].command == "monitor"
    assert messages[3].command == "monitor"
    assert messages[4].command == "checkpoint"
    # Check that we move the stepper first
    assert messages[5].command == "set"
    assert messages[5].args == (-100,)
    assert messages[6].command == "wait"
    # Check that flyer motor positions snake back and forth
    stepper_positions = [
        msg.args[0] for msg in messages if (msg.command == "set" and msg.obj is stepper)
    ]
    flyer_start_positions = [
        msg.args[0].start_position
        for msg in messages
        if (msg.command == "prepare" and msg.obj is flyer)
    ]
    flyer_end_positions = [
        msg.args[0].end_position
        for msg in messages
        if (msg.command == "prepare" and msg.obj is flyer)
    ]
    assert stepper_positions == list(np.linspace(-100, 100, num=11))
    assert flyer_start_positions == [-20, 30, -20, 30, -20, 30, -20, 30, -20, 30, -20]
    assert flyer_end_positions == [30, -20, 30, -20, 30, -20, 30, -20, 30, -20, 30]


async def test_fly_grid_scan_metadata(sim_registry, flyer, ion_chamber):
    """Does the plan set the parameters of the flyer motor."""
    stepper = Motor(name="stepper", prefix="")
    await stepper.connect(mock=True)
    md = {"spam": "eggs"}
    plan = grid_fly_scan(
        [ion_chamber],
        stepper,
        -100,
        100,
        11,
        flyer,
        -20,
        30,
        6,
        dwell_time=1.0,
        snake_axes=[flyer],
        md=md,
    )
    # Check the metadata contained in the "open_run" message
    messages = list(plan)
    open_msg = messages[2]
    assert open_msg.command == "open_run"
    real_md = open_msg.kwargs
    expected_md = {
        "motors": (stepper.name, flyer.name),
        "num_points": 66,
        "num_intervals": 65,
        "plan_args": {
            "detectors": [repr(ion_chamber)],
            "args": [repr(stepper), -100, 100, 11, repr(flyer), -20, 30, 6],
            "dwell_time": 1.0,
            "trigger": "DetectorTrigger.INTERNAL",
            "delay_outputs": [],
            "snake_axes": [repr(flyer)],
        },
        "plan_name": "grid_fly_scan",
        "hints": {
            "gridding": "rectilinear",
            "dimensions": [([stepper.name], "primary"), ([flyer.name], "primary")],
        },
        "shape": (11, 6),
        "extents": ([-100, 100], [-20, 30]),
        "snaking": [False, True],
        "plan_pattern": "outer_product",
        "plan_pattern_args": {
            "args": [
                repr(stepper),
                -100,
                100,
                11,
                repr(flyer),
                -20,
                30,
                6,
            ]
        },
        "plan_pattern_module": "bluesky.plan_patterns",
        "spam": "eggs",
    }
    assert real_md == expected_md


def test_prepare_detectors_old():
    delay = DG645Delay("")
    # Include two ion chambers to make sure we set the delay outputs only once
    ion_chamber = IonChamber(
        "",
        scaler_channel=2,
        preamp_prefix="",
        voltmeter_prefix="",
        voltmeter_channel=0,
        counts_per_volt_second=1e6,
    )
    ion_chamber2 = IonChamber(
        "",
        scaler_channel=2,
        preamp_prefix="",
        voltmeter_prefix="",
        voltmeter_channel=0,
        counts_per_volt_second=1e6,
    )
    trigger_info = TriggerInfo(
        number_of_events=15,
        livetime=1.5,
    )
    ion_chamber.validate_trigger_info = mock.MagicMock(return_value=trigger_info)
    ion_chamber2.validate_trigger_info = mock.MagicMock(return_value=trigger_info)
    xspress = Xspress3Detector("")
    gate_info = TriggerInfo(
        number_of_events=15,
        livetime=1.5,
        deadtime=0.1,
    )
    xspress.validate_trigger_info = mock.MagicMock(return_value=gate_info)
    msgs = list(
        prepare_detectors(
            detectors=[ion_chamber, ion_chamber2, xspress],
            trigger_info=trigger_info,
            delay_outputs=[delay.output_AB, delay.output_AB, delay.output_CD],
        )
    )
    # Ion chamber trigger
    assert len(msgs) == 6
    assert msgs[0].obj is ion_chamber
    assert msgs[0].command == "prepare"
    assert msgs[0].args == (trigger_info,)
    assert msgs[1].obj is ion_chamber2
    assert msgs[1].command == "prepare"
    assert msgs[1].args == (trigger_info,)
    # Xspress
    assert msgs[2].obj is xspress
    assert msgs[2].command == "prepare"
    assert msgs[2].args == (gate_info,)
    # Delay generator
    assert msgs[3].obj is delay
    assert msgs[3].command == "prepare"
    assert msgs[3].args == (trigger_info,)
    assert msgs[4].obj is delay.output_AB
    assert msgs[4].command == "prepare"
    assert msgs[4].args == (trigger_info,)
    assert msgs[5].obj is delay.output_CD
    assert msgs[5].command == "prepare"
    assert msgs[5].args == (gate_info,)


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
