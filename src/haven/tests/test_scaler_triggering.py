"""The scaler has a global trigger, but individual channels.

These tests check the system for monitoring the trigger system in
bluesky so that it only fires the trigger once for all of the scaler
channels. Additionally, the scaler can send that trigger to other
devices, like the Xspress3 fluorescence detector readout electronics.

"""

import pytest
from ophyd import Device

from haven.instrument.scaler_triggered import ScalerTriggered


@pytest.mark.skip("scaler_triggering is not needed right now")
def test_trigger_fires():
    scaler_prefix = "myioc:myscaler"
    # Prepare the scaler triggered device
    MyDevice = type("MyDevice", (ScalerTriggered, Device), {})
    device = MyDevice(name="device", scaler_prefix=scaler_prefix)
    # Make sure it's in a sensible starting state
    assert hasattr(device, "_statuses")
    assert len(device._statuses) == 0
    # Trigger the device
    device.trigger()
    # Check that a status was added
    assert len(device._statuses) == 1
    # Check that triggering again is indempotent
    first_status = device._statuses[scaler_prefix]
    old_done = first_status.__class__.done
    first_status.__class__.done = False
    try:
        device.trigger()
    except Exception:
        pass
    finally:
        first_status.__class__.done = old_done
    second_status = device._statuses[scaler_prefix]
    assert first_status is second_status


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
