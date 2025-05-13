import asyncio

from ophyd_async.core import Device
from ophydregistry import Registry
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QAbstractItemView, QListView


class DetectorListView(QListView):
    detector_model: QStandardItemModel
    registry: Registry

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Create the data model
        self.detector_model = QStandardItemModel()
        self.setModel(self.detector_model)
        # Make it possible to select multiple detectors
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    async def update_devices(self, registry: Registry):
        self.registry = registry
        # Get devices
        detectors = registry.findall(label="detectors", allow_none=True)
        # Remove old detectors list from model
        model = self.detector_model
        model.removeRows(0, model.rowCount())
        # Add new detectors to model
        for det in detectors:
            model.appendRow(QStandardItem(det.name))

    def selected_detectors(self) -> list[Device]:
        indexes = self.selectedIndexes()
        items = [self.detector_model.itemFromIndex(i) for i in indexes]
        names = [item.text() for item in items]
        devices = [self.registry[name] for name in names]
        return devices

    async def acquire_times(self) -> list[float]:
        devices = self.selected_detectors()
        devices = [
            device for device in devices if hasattr(device, "default_time_signal")
        ]
        aws = [device.default_time_signal.get_value() for device in devices]
        times = await asyncio.gather(*aws)
        return times


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
