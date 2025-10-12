import pytest
from bluesky import plan_stubs as bps

from haven.preprocessors import aps_suspenders_wrapper


@pytest.fixture()
def feature_flag(mocker):
    # Mock the feature flag for now
    mock_config = mocker.MagicMock()
    mock_config.feature_flag.return_value = True
    mocker.patch("haven.preprocessors.aps_suspenders.load_config", mock_config)
    return mock_config


def test_storage_ring_current_suspender(aps, feature_flag):
    # Simulate a valid read on the APS status
    wrapped = aps_suspenders_wrapper(bps.null(), aps)
    msgs = list(wrapped)
    assert msgs[0].command == "read"
    assert msgs[0].obj is aps.machine_status
    # Get the rest of the messages
    assert msgs[1].command == "install_suspender"
    assert msgs[2].command == "install_suspender"
    assert msgs[3].command == "null"
    assert msgs[4].command == "remove_suspender"
    assert msgs[5].command == "remove_suspender"


def test_not_user_mode(aps, feature_flag):
    # Simulate a valid read on the APS status
    wrapped = aps_suspenders_wrapper(bps.null(), aps)
    msg = next(wrapped)
    assert msg.command == "read"
    assert msg.obj is aps.machine_status
    # Check that we only read the machine status and run the internal plan
    status_reading = {"aps.machine_status.name": {"value": "MAINTENANCE"}}
    msgs = [msg, wrapped.send(status_reading), *wrapped]
    assert msgs[1].command == "null"
    assert len(msgs) == 2


def test_without_feature_flag(aps):
    # Simulate a valid read on the APS status
    wrapped = aps_suspenders_wrapper(bps.null(), aps)
    msgs = list(wrapped)
    assert len(msgs) == 1
    assert msgs[0].command == "null"


def test_open_shutters(aps, shutters, feature_flag):
    shutter = shutters[0]
    plan = aps_suspenders_wrapper(bps.null(), aps=aps, shutters=[shutter])
    msgs = list(plan)
    permit_suspender = msgs[1].args[0]
    open_shutters_plan = permit_suspender._post_plan
    shutter_msgs = list(open_shutters_plan())
    assert shutter_msgs[0].command == "set"
    assert shutter_msgs[0].obj is shutter
    assert shutter_msgs[0].args[0] == 0


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2025, UChicago Argonne, LLC
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
