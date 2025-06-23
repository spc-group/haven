from pathlib import Path
from typing import Mapping, Optional, Sequence

from ophyd import Device
from pydm import Display
from qtpy.QtCore import Signal

from haven import beamline


class FireflyDisplay(Display):
    caqtdm_ui_file: str = ""
    caqtdm_command: str = "/APSshare/bin/caQtDM -style plastique -noMsg -attach"
    caqtdm_actions: Sequence
    device: Optional[Device]
    registry = None
    _bss_metadata: Mapping[str, str] = {}

    # Signals
    status_message_changed = Signal(str, int)
    queue_item_submitted = Signal(object)
    execute_item_submitted = Signal(object)
    device_window_requested = Signal(str)  # device name

    def __init__(self, parent=None, args=None, macros=None, ui_filename=None, **kwargs):
        super().__init__(
            parent=parent, args=args, macros=macros, ui_filename=ui_filename, **kwargs
        )
        self.customize_device()
        self.customize_ui()

    async def update_devices(self, registry):
        """The list of accessible devices has changed."""
        self.registry = registry

    def customize_device(self):
        # Retrieve the device
        device = self.macros().get("DEVICE")
        if device is not None:
            device = beamline.devices[device]
        self.device = device
        return device

    def customize_ui(self):
        pass

    def update_bss_metadata(self, md: Mapping[str, str]):
        self._bss_metadata = md

    def update_queue_status(self, status):
        pass

    def show_message(self, message: str, timeout: int = 0):
        """Display a message in the status bar."""
        self.status_message_changed.emit(str(message), timeout)

    def ui_filename(self):
        raise NotImplementedError

    def ui_filepath(self):
        path_base = Path(__file__).parent
        return path_base / self.ui_filename()


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
