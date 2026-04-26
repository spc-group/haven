from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QStyledItemDelegate

from .style import DM_GUI_BLUE, DM_GUI_DARK_BLUE


class CustomStyledDelegate(QStyledItemDelegate):
    def __init__(self, tableView, parent):
        super(CustomStyledDelegate, self).__init__(parent)
        self.parent = parent
        self.tableView = tableView
        self.rowColor = DM_GUI_BLUE
        self.cellColor = DM_GUI_DARK_BLUE

    def paint(self, painter, option, index):
        selectedIdx, selectedRows = self.parent.parent.getSelectedIndex(self.tableView)
        if len(selectedIdx) == 1:
            if selectedIdx[0] == index:
                painter.fillRect(option.rect, self.cellColor)
                painter.drawText(
                    option.rect,
                    Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignVCenter,
                    self.__getData(index),
                )
            elif selectedIdx[0].row() == index.row():
                painter.fillRect(option.rect, self.rowColor)
                painter.drawText(
                    option.rect,
                    Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignVCenter,
                    self.__getData(index),
                )
            else:
                super(CustomStyledDelegate, self).paint(painter, option, index)
        elif len(selectedIdx) > 1:
            if index.row() in selectedRows:
                painter.fillRect(option.rect, self.rowColor)
                painter.drawText(
                    option.rect,
                    Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignVCenter,
                    self.__getData(index),
                )
            else:
                super(CustomStyledDelegate, self).paint(painter, option, index)
        else:
            super(CustomStyledDelegate, self).paint(painter, option, index)

    def __getData(self, index):
        return str(index.model().data(index, Qt.DisplayRole))
