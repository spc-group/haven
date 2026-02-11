import pytest_asyncio

from haven.devices.asymmotron import Analyzer
from haven.plans._emission_map_scan import emission_map_scan


@pytest_asyncio.fixture()
async def analyzer():
    xtal = Analyzer(
        name="analyzer",
        chord_motor_prefix="",
        pitch_motor_prefix="",
        yaw_motor_prefix="",
        prefix="",
    )
    await xtal.connect(mock=True)
    return xtal


def test_plan_messages(ion_chamber, mono, undulator, analyzer):
    plan = emission_map_scan(
        [ion_chamber],
        [analyzer],
        [8300, 8320, 8340],
        [mono, undulator],
        [8500, 8600, 8700],
    )
    msgs = list(plan)
    from pprint import pprint

    pprint(msgs)
    set_msgs = [msg for msg in msgs if msg.command == "set"]
    # Check the first step
    assert set_msgs[0].command == "set"
    assert set_msgs[0].obj == analyzer
    assert set_msgs[0].args == (8300,)
    assert set_msgs[1].command == "set"
    assert set_msgs[1].obj == mono
    assert set_msgs[1].args == (8500,)
    assert set_msgs[2].command == "set"
    assert set_msgs[2].obj == undulator
    assert set_msgs[2].args == (8500,)
    # Check that the fast axis gets moved for the second step
    assert set_msgs[3].command == "set"
    assert set_msgs[3].obj == mono
    assert set_msgs[3].args == (8600,)
    assert set_msgs[4].command == "set"
    assert set_msgs[4].obj == undulator
    assert set_msgs[4].args == (8600,)


def test_metadata(ion_chamber, mono, undulator, analyzer):
    plan = emission_map_scan(
        [ion_chamber],
        [analyzer],
        [8300, 8320, 8340],
        [mono, undulator],
        [8500, 8600, 8700],
    )
    msgs = list(plan)
    open_run_msg = msgs[4]
    md = open_run_msg.kwargs
    assert md["num_points"] == 9
    assert md["num_intervals"] == 8
    assert md["plan_name"] == "emission_map_scan"
    hints = set(
        [val for values, streams in md["hints"]["dimensions"] for val in values]
    )
    assert hints == {
        "analyzer-energy",
        "monochromator-bragg",
        "monochromator-energy",
        "undulator-energy",
    }


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
