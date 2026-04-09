import numpy as np
import pytest
from ophyd_async.core import DetectorTrigger, TriggerInfo
from ophyd_async.epics.motor import Motor
from scanspec.core import Path
from scanspec.specs import Fly, Line

from haven.devices import (
    SoftGlueFlyerController,
    Xspress3Detector,
)
from haven.plans._fly import _grid_scan_spec, fly_scan, fly_segment, grid_fly_scan


@pytest.fixture()
def flyer():
    fly_motor = Motor("255idcVME:m1", name="flyer")
    return fly_motor


@pytest.fixture()
def stepper():
    step_motor = Motor("255idcVME:m2", name="stepper")
    return step_motor


@pytest.fixture()
def controller():
    device = SoftGlueFlyerController(prefix="spam_eggs:", name="soft_glue_delay")
    return device


@pytest.fixture()
def xspress():
    xsp = Xspress3Detector(prefix="XSP3:", name="xspress")
    return xsp


def test_fly_segment(flyer, xspress):
    spec = Line(flyer, -10, 10, 6)
    trigger_info = TriggerInfo(
        trigger=DetectorTrigger.EXTERNAL_EDGE, number_of_events=6
    )
    plan = fly_segment([xspress], motors=[flyer], spec=spec, trigger_info=trigger_info)
    msgs = list(plan)
    assert len(msgs) > 2
    # Prepare the scan
    assert msgs[0].command == "prepare"
    assert msgs[0].obj is flyer
    assert msgs[1].command == "prepare"
    assert msgs[1].obj is xspress
    assert msgs[1].args[0].trigger == DetectorTrigger.EXTERNAL_EDGE
    assert msgs[2].command == "wait"
    assert msgs[3].command == "declare_stream"
    assert msgs[3].args[0] is xspress
    # Start the scan
    assert msgs[4].command == "checkpoint"
    assert msgs[5].command == "monitor"
    assert msgs[5].obj is flyer
    assert msgs[6].command == "kickoff"
    assert msgs[6].obj is xspress
    assert msgs[7].command == "wait"
    assert msgs[8].command == "kickoff"
    assert msgs[8].obj is flyer
    assert msgs[9].command == "wait"
    # Finish the scan
    assert msgs[10].command == "complete"
    assert msgs[10].obj is flyer
    assert msgs[11].command == "wait"
    assert msgs[12].command == "complete"
    assert msgs[12].obj is xspress
    assert msgs[13].command == "wait"
    assert msgs[14].command == "collect"
    assert msgs[14].obj is xspress
    assert msgs[15].command == "unmonitor"
    assert msgs[15].obj is flyer


def test_fly_segment_controller_triggers(flyer, xspress, controller, monkeypatch):
    """Flyer controllers can provide additional trigger info for detectors."""
    spec = Line(flyer, -10, 10, 6)
    trigger_info = TriggerInfo(
        trigger=DetectorTrigger.EXTERNAL_EDGE, number_of_events=6
    )
    plan = fly_segment(
        [xspress],
        motors=[flyer],
        spec=spec,
        trigger_info=trigger_info,
        flyer_controllers=[controller],
    )
    monkeypatch.setattr(
        controller,
        "extra_trigger_infos",
        lambda t: [TriggerInfo(trigger=DetectorTrigger.EXTERNAL_LEVEL)],
        raising=False,
    )
    # Prepare the scan
    msg = next(plan)
    assert msg.command == "prepare"
    assert msg.obj is flyer
    msg = next(plan)
    assert msg.command == "prepare"
    assert msg.obj is controller
    # Make sure we accomodate detectors that don't support edge triggers
    msg = next(plan)
    assert msg.command == "prepare"
    assert msg.obj is xspress
    assert msg.args[0].trigger == DetectorTrigger.EXTERNAL_LEVEL


def test_line_prepares_flyer_path(flyer):
    """Does the plan set the parameters of the flyer motor?"""
    # step size == 10
    plan = fly_scan([], flyer, -20, 30, num=6, dwell_time=1.5)
    messages = list(plan)
    prep_msg = [
        msg for msg in messages if msg.command == "prepare" and msg.obj is flyer
    ][0]
    prep_path = prep_msg.args[0]
    assert isinstance(prep_path, Path)
    points = prep_path.consume()
    np.testing.assert_equal(points.midpoints[flyer], np.linspace(-20, 30, num=6))
    np.testing.assert_equal(points.lower[flyer], np.linspace(-25, 25, num=6))
    np.testing.assert_equal(points.upper[flyer], np.linspace(-15, 35, num=6))
    np.testing.assert_equal(points.duration, np.full(shape=(6,), fill_value=1.5))


def test_line_prepares_controller_path(flyer, controller):
    """Does the plan set the parameters of the flyer controller?"""
    plan = fly_scan(
        [], flyer, -20, 30, num=6, dwell_time=1.5, flyer_controllers=[controller]
    )
    messages = list(plan)
    prep_msg = [
        msg for msg in messages if msg.command == "prepare" and msg.obj is controller
    ][0]
    prep_info = prep_msg.args[0]
    assert isinstance(prep_info, TriggerInfo)


def test_fly_scan_metadata(flyer, ion_chamber):
    """Does the plan set the parameters of the flyer motor."""
    md = {"spam": "eggs"}
    plan = fly_scan([ion_chamber], flyer, -20, 30, num=6, dwell_time=1, md=md)
    messages = list(plan)
    assert messages[0].command == "stage"
    assert messages[1].command == "stage"
    open_msg = messages[2]
    assert open_msg.command == "open_run"
    real_md = open_msg.kwargs
    spec = Fly(1 @ Line(flyer, -20, 30, 6))
    expected_md = {
        "plan_args": {
            "detectors": list([repr(ion_chamber)]),
            "num": 6,
            "dwell_time": 1,
            "flyer_controllers": [],
            "trigger": "INTERNAL",
            "*args": (repr(flyer), -20, 30),
        },
        "scanspec": repr(spec),
        "plan_name": "fly_scan",
        "motors": [flyer.name],
        "detectors": [ion_chamber.name],
        "spam": "eggs",
    }
    assert real_md == expected_md


grid_specs = [
    # (
    #     motor args,
    #     snaking,
    #     dwell_time,
    #     expected_spec,
    # ),
    (
        ("y", -20, 20, 6, "x", -10, 10, 11),
        True,
        1.5,
        Line("y", -20, 20, 6) * Fly(1.5 @ ~Line("x", -10, 10, 11)),
    ),
    (
        ("y", -20, 20, 6, "x", -10, 10, 11),
        ["x"],
        1.5,
        Line("y", -20, 20, 6) * Fly(1.5 @ ~Line("x", -10, 10, 11)),
    ),
]


@pytest.mark.parametrize("args,snaking,dwell_time,spec", grid_specs)
def test_grid_scan_spec(args, snaking, dwell_time, spec):
    assert _grid_scan_spec(*args, dwell_time=dwell_time, snake_axes=snaking) == spec


def test_grid_scan_path():
    """Confirm that we can get snaked points in both directions."""
    spec = Line("y", -20, 20, 6) * Fly(1.5 @ ~Line("x", -10, 10, 11))
    path = Path(spec.calculate(), start=11, num=11)
    points = path.consume()
    np.testing.assert_equal(points.midpoints["x"], np.linspace(10, -10, num=11))


def test_grid_fly_scan_setup(flyer, stepper, xspress, controller):
    plan = grid_fly_scan(
        [xspress],
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
        flyer_controllers=[controller],
    )
    messages = list(plan)
    # Check initial setup messages
    assert messages[0].command == "stage"
    assert messages[0].obj is stepper
    assert messages[1].command == "stage"
    assert messages[1].obj is flyer
    assert messages[2].command == "stage"
    assert messages[2].obj is controller
    assert messages[3].command == "open_run"
    # Detectors are staged per-line later in the plan
    assert messages[8].command == "stage"
    assert messages[8].obj is xspress


def test_grid_fly_scan_stepper_positions(flyer, stepper, xspress, controller):
    plan = grid_fly_scan(
        [xspress],
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
        flyer_controllers=[controller],
    )
    messages = list(plan)
    # Check stepper positions
    step_msgs = [msg for msg in messages if msg.command == "set" and msg.obj is stepper]
    np.testing.assert_equal(
        [msg.args[0] for msg in step_msgs], np.linspace(-100, 100, num=11)
    )


def test_grid_fly_scan_flyer_paths(flyer, stepper, xspress, controller):
    num_steps = 11
    plan = grid_fly_scan(
        [xspress],
        stepper,
        -100,
        100,
        num_steps,
        flyer,
        -20,
        30,
        6,
        dwell_time=1.0,
        snake_axes=[flyer],
        flyer_controllers=[controller],
    )
    messages = list(plan)
    # Check stepper positions
    flyer_paths = [
        msg.args[0] for msg in messages if msg.command == "prepare" and msg.obj is flyer
    ]
    assert len(flyer_paths) == num_steps
    # Make sure the paths are snaking
    np.testing.assert_equal(
        flyer_paths[0].consume().midpoints[flyer], np.linspace(-20, 30, num=6)
    )
    np.testing.assert_equal(
        flyer_paths[1].consume().midpoints[flyer], np.linspace(30, -20, num=6)
    )


def test_grid_prepare_controllers(flyer, stepper, xspress, controller):
    num_steps = 11
    num_points = 6
    plan = grid_fly_scan(
        [xspress],
        stepper,
        -100,
        100,
        num_steps,
        flyer,
        -20,
        30,
        num_points,
        dwell_time=1.0,
        snake_axes=[flyer],
        flyer_controllers=[controller],
    )
    messages = list(plan)
    # Check controller prepare args
    controller_args = [
        msg.args
        for msg in messages
        if msg.command == "prepare" and msg.obj is controller
    ]
    assert len(controller_args) == num_steps
    first_trigger_info = controller_args[0][0]
    assert first_trigger_info.number_of_events == num_points


async def test_fly_grid_scan_metadata(sim_registry, flyer, ion_chamber, stepper):
    """Does the plan set the parameters of the flyer motor."""
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
    open_run_messages = [msg for msg in messages if msg.command == "open_run"]
    assert len(open_run_messages) == 1
    real_md = open_run_messages[0].kwargs
    spec = Line(stepper, -100, 100, 11) * Fly(1.0 @ ~Line(flyer, -20, 30, 6))
    expected_md = {
        "motors": (stepper.name, flyer.name),
        "num_points": 66,
        "num_intervals": 55,
        "plan_args": {
            "detectors": [repr(ion_chamber)],
            "args": [repr(stepper), -100, 100, 11, repr(flyer), -20, 30, 6],
            "dwell_time": 1.0,
            "trigger": "INTERNAL",
            "flyer_controllers": [],
            "snake_axes": [repr(flyer)],
            "md": {"spam": "eggs"},
        },
        "scanspec": repr(spec),
        "plan_name": "grid_fly_scan",
        "hints": {
            "gridding": "rectilinear",
            "dimensions": [([stepper.name], "primary"), ([flyer.name], "primary")],
        },
        "shape": (11, 6),
        "extents": [
            (-100, 100),
            (-20, 30),
        ],
        "snaking": (False, True),
        "plan_pattern": "outer_product",
        "spam": "eggs",
    }
    assert real_md == expected_md


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
