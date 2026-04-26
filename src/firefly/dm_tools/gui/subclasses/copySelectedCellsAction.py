from PyQt5.QtWidgets import QAction, QApplication


class CopySelectedCellsAction(QAction):
    def __init__(self, parent):
        super(CopySelectedCellsAction, self).__init__("Copy", parent)
        self.setShortcut("Ctrl+C")
        self.triggered.connect(self.copyToClipboard)
        self.parent = parent

    def copyToClipboard(self):
        if len(self.parent.selectionModel().selectedIndexes()) > 0:
            previous = self.parent.selectionModel().selectedIndexes()[0]
            columns = []
            rows = []
            for index in self.parent.selectionModel().selectedIndexes():
                if previous.column() != index.column():
                    columns.append(rows)
                    rows = []
                #                rows.append(str(index.data().toString()))
                rows.append(str(index.data()))
                previous = index
            columns.append(rows)

            clipboard = ""
            nrows = len(columns[0])
            ncols = len(columns)
            for row in range(nrows):
                for col in range(ncols):
                    clipboard += columns[col][row]
                    if col != (ncols - 1):
                        clipboard += "\t"
                clipboard += "\n"

            sysclip = QApplication.clipboard()
            sysclip.setText(clipboard)
