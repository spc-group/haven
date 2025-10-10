import pytest
from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from ophyd import sim

from haven.plans import align_motor

# from run_engine import RunEngineStub


@pytest.mark.skip(reason="Deprecated, use bluesky.plans.tune_centroid")
def test_align_motor(ffapp):
    # Set up simulated motors and detectors
    motor = sim.SynAxis(name="motor", labels={"motors"})
    detector = sim.SynGauss(
        name="detector",
        motor=motor,
        motor_field="motor",
        center=-3,
        Imax=1,
        sigma=20,
        labels={"detectors"},
    )
    # Prepare the callback to check results
    bec = BestEffortCallback()
    bec.disable_plots()
    bec.disable_table()
    # Prepare the plan
    plan = align_motor(
        detector=detector,
        motor=motor,
        distance=40,
        bec=bec,
        md={"plan_name": "test_plan"},
    )
    # Execute the plan
    RE = RunEngine(call_returns_result=True)
    result = RE(plan)
    # Check peak calculation results
    assert bec.peaks["cen"]["detector"] == pytest.approx(-3, rel=1e-3)
    assert motor.readback.get() == pytest.approx(-3, rel=1e-3)


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
