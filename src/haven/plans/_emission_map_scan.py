import operator
from collections.abc import Sequence
from functools import reduce
from typing import Any

import bluesky.plans as bp
from bluesky.plans import PerStep, partition
from bluesky.protocols import Movable, Readable
from bluesky.utils import (
    CustomPlanMetadata,
    MsgGenerator,
)
from cycler import cycler


def emission_map_scan(
    detectors: Sequence[Readable],
    *args: tuple[Movable | Any, list[Any]],
    per_step: PerStep | None = None,
    md: CustomPlanMetadata | None = None,
) -> MsgGenerator[str]:
    """A Bluesky plan for doing emission (a.k.a. RXES or RIXS) maps."""
    cyclers = []
    for movers, pos_list in partition(2, args):
        axis_cyclers = [cycler(mover, pos_list) for mover in movers]
        cyclers.append(reduce(operator.add, axis_cyclers))
    plan_cycler = reduce(operator.mul, cyclers)
    # Add plan-specific metadata
    md_args = []
    motor_names = []
    motors = []
    for i, (movers, pos_list) in enumerate(partition(2, args)):  # noqa: B007
        mover_reprs = [repr(mover) for mover in movers]
        md_args.extend([mover_reprs, pos_list])
        motor_names.extend([mover.name for mover in movers])
        motors.extend(movers)
    _md = {
        "shape": tuple(len(pos_list) for motor, pos_list in partition(2, args)),
        "extents": tuple(
            [min(pos_list), max(pos_list)] for motor, pos_list in partition(2, args)
        ),
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "args": md_args,
            "per_step": repr(per_step),
        },
        "plan_name": "emission_map_scan",
        "motors": tuple(motor_names),
        "hints": {},
    }
    _md.update(md or {})
    try:
        motor_hints = [(m.hints["fields"], "primary") for m in motors]
        assert isinstance(_md["hints"], dict), "Hints must be a dictionary"
        _md["hints"].setdefault("dimensions", motor_hints)
    except (AttributeError, KeyError):
        ...
    return (yield from bp.scan_nd(detectors, plan_cycler, md=_md))


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2026, UChicago Argonne, LLC
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
