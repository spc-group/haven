from PyQt5.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QListView

from haven import registry


class DetectorListView(QListView):
    detector_model: QStandardItemModel

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_detector_items()

    def load_detector_items(self):
        detectors = registry.findall(label="detectors", allow_none=True)
        self.detector_model = QStandardItemModel()
        self.setModel(self.detector_model)
        for det in detectors:
            self.detector_model.appendRow(QStandardItem(det.name))

    def selected_detectors(self):
        indexes = self.selectedIndexes()
        items = [self.detector_model.itemFromIndex(i) for i in indexes]
        names = [item.text() for item in items]
        return names
