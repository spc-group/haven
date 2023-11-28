import json
import logging

from pydm.widgets import PyDMEmbeddedDisplay

import haven
from firefly import display

log = logging.getLogger(__name__)


class CamerasDisplay(display.FireflyDisplay):
    _camera_displays = []

    def __init__(self, args=None, macros={}, **kwargs):
        self._camera_displays = []
        super().__init__(args=args, macros=macros, **kwargs)

    def customize_ui(self):
        # Delete existing camera widgets
        for idx in reversed(range(self.cameras_layout.count())):
            self.cameras_layout.takeAt(idx).widget().deleteLater()
        # Add embedded displays for all the cameras
        try:
            cameras = haven.registry.findall(label="cameras")
        except haven.exceptions.ComponentNotFound:
            log.warning(
                "No cameras found, [Detectors] -> [Cameras] panel will be empty."
            )
            cameras = []
        for camera in sorted(cameras, key=lambda c: c.name):
            disp = PyDMEmbeddedDisplay(parent=self)
            disp.macros = json.dumps(
                {
                    "CAMERA": camera.name,
                    "DESC": camera.description,
                }
            )
            disp.filename = "camera.py"
            # Add the Embedded Display to the Results Layout
            self.cameras_layout.addWidget(disp)
            self._camera_displays.append(disp)

    def ui_filename(self):
        return "cameras.ui"


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
