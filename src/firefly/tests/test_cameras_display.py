import json

import pytest
from pydm.widgets.channel import PyDMChannel
from qtpy import QtCore, QtGui, QtWidgets

from firefly.camera import CameraDisplay, DetectorStates
from firefly.cameras import CamerasDisplay

macros = {"PREFIX": "camera_ioc:", "DESC": "Camera A"}


@pytest.fixture()
def cameras_display(qtbot, sim_camera):
    display = CamerasDisplay()
    qtbot.addWidget(display)
    return display


@pytest.fixture()
def camera_display(qtbot, sim_camera):
    display = CameraDisplay()
    qtbot.addWidget(display)
    return display


def test_embedded_displays(cameras_display, sim_camera):
    """Test that the embedded displays get loaded."""
    display = cameras_display
    # Check that the embedded display widgets get added correctly
    assert hasattr(display, "_camera_displays")
    assert len(display._camera_displays) == 1
    # Check the embedded display macros
    # assert isinstance(display._camera_displays[0].macros, dict)
    expected_macros = {"CAMERA": sim_camera.name, "DESC": sim_camera.description}
    assert json.loads(display._camera_displays[0].macros) == expected_macros


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
