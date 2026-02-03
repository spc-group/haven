# Tests to check the integration of Haven with Tiled

import pytest
from ophyd_async import sim
from ophyd_async.core import init_devices

from haven import run_engine, tiled_writer
from haven.plans import scan


@pytest.mark.slow
def test_streams(tiled_server):
    writer = tiled_writer({"writer_profile": "tiled_writable"})
    RE = run_engine(tiled_writer=writer, call_returns_result=True)
    # Prepare ophyd-async devices
    pattern_generator = sim.PatternGenerator()
    with init_devices():
        stage = sim.SimStage(pattern_generator)
        pdet = sim.SimPointDetector(pattern_generator)
    # Execute the plan
    plan = scan([pdet], stage.x, -0.628318, 0.628318, 5)
    result = RE(plan)
    # Check that the correct streams were written
    assert result.exit_status == "success"
    (uid,) = result.run_start_uids
    assert list(writer.client[uid].keys()) == ["primary"]


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
