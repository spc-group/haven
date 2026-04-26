from PyQt5.QtCore import QItemSelection, QItemSelectionModel, QModelIndex


class CustomSelectionModel(QItemSelectionModel):
    def __init__(self, parent, model):
        super(CustomSelectionModel, self).__init__(model)
        self.parent = parent
        self.model = model

    def select(self, selection, flags):
        if isinstance(selection, QItemSelection):
            deselectIdx = self.selection()
            super(CustomSelectionModel, self).select(selection, flags)
            self.selectionChanged(deselectIdx, selection)
        elif isinstance(selection, QModelIndex):
            # super(CustomSelectionModel, self).select(selection, flags)
            pass
        else:
            raise Exception("Unexpected type for arg0: '%s'" % type(selection))

    def selectionChanged(self, deselect, select):
        deselectedIdxs = deselect.indexes()
        selectedIdxs = select.indexes()
        for index in deselectedIdxs:
            for colIdx in range(self.model.columnCount()):
                self.parent.updateView(self.model.index(index.row(), colIdx))
        for index in selectedIdxs:
            for colIdx in range(self.model.columnCount()):
                self.parent.updateView(self.model.index(index.row(), colIdx))
