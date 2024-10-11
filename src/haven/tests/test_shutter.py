import pytest
from ophyd import sim
from ophyd.utils.errors import ReadOnlyError

from haven.devices.shutter import PssShutter, ShutterState


@pytest.fixture()
def shutter(sim_registry):
    shutter = sim.instantiate_fake_device(PssShutter, name="shutter")
    return shutter


def test_shutter_setpoint(shutter):
    """When we open and close the shutter, do the right EPICS signals get
    set?

    """
    shutter.open_signal.sim_put(0)
    shutter.close_signal.sim_put(0)
    # Close the shutter
    shutter.open_signal.sim_put(0)
    shutter.close_signal.sim_put(0)
    status = shutter.set(ShutterState.CLOSED)
    shutter.readback.sim_put(ShutterState.CLOSED)
    status.wait(timeout=1)
    assert shutter.open_signal.get() == 0
    assert shutter.close_signal.get() == 1
    # Open the shutter
    shutter.close_signal.sim_put(0)
    shutter.open_signal.sim_put(0)
    status = shutter.set(ShutterState.OPEN)
    shutter.readback.sim_put(ShutterState.OPEN)
    status.wait(timeout=1)
    assert shutter.open_signal.get() == 1
    assert shutter.close_signal.get() == 0


def test_shutter_check_value(shutter):
    # Check for non-sense values
    with pytest.raises(ValueError):
        shutter.set(ShutterState.FAULT)
    # Test shutter allow_close
    shutter.allow_close = False
    with pytest.raises(ReadOnlyError):
        shutter.set(ShutterState.CLOSED)
    # Test shutter allow_open
    shutter.allow_open = False
    with pytest.raises(ReadOnlyError):
        shutter.set(ShutterState.OPEN)


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
