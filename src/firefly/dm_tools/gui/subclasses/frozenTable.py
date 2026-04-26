#!/usr/bin/env python

from PyQt5.QtCore import QSortFilterProxyModel, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QAbstractItemView, QTableView


# Makes a table with two views, one for a table of background data and one that has one row frozen to the top of the model.
# This row will stay in place for vertical scrolling and match any horizontal scrolling.  The same applies to resizing.
class FreezeTableWidget(QTableView):
    def __init__(self, parent, model):
        # QTableView.__init__(self, parent)
        super(FreezeTableWidget, self).__init__(parent)
        self.parent = parent
        self.freezeTableConstructor()

    def freezeTableConstructor(self):
        # set the table model
        self.tm = QStandardItemModel()
        self.tm.setHorizontalHeaderLabels("Username;First;Last;Email;".split(";"))
        self.tm.setItem(0, 0, QStandardItem())
        self.tm.setItem(0, 1, QStandardItem())
        self.tm.setItem(0, 2, QStandardItem())
        self.tm.setItem(0, 3, QStandardItem())
        self.tm.removeColumn(4)

        # set the proxy model
        pm = QSortFilterProxyModel(self)
        pm.setSourceModel(self.tm)
        self.setModel(pm)

        self.frozenTableView = QTableView(self)
        self.frozenTableView.setModel(pm)
        self.frozenTableView.verticalHeader().hide()
        self.frozenTableView.setFocusPolicy(Qt.NoFocus)
        self.frozenTableView.horizontalHeader().setStretchLastSection(True)
        self.frozenTableView.horizontalHeader().sortIndicatorChanged.connect(
            self.sortIndicatorChanged
        )
        self.frozenTableView.setStyleSheet("""border: none;""")

        self.frozenTableView.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.frozenTableView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewport().stackUnder(self.frozenTableView)
        self.setEditTriggers(QAbstractItemView.SelectedClicked)

        hh = self.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignCenter)
        hh.setStretchLastSection(True)
        nrow = self.tm.rowCount()
        for row in range(nrow):
            if row == 0:
                continue
            else:
                self.frozenTableView.setRowHidden(row, True)
        self.setAlternatingRowColors(True)
        vh = self.verticalHeader()
        vh.setDefaultAlignment(Qt.AlignCenter)
        vh.setVisible(True)

        self.frozenTableView.verticalHeader().setDefaultSectionSize(
            vh.defaultSectionSize()
        )
        self.frozenTableView.show()
        self.updateFrozenTableGeometry()
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.frozenTableView.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        # connect the headers and scrollbars of both tableviews together
        self.frozenTableView.horizontalHeader().sectionResized.connect(
            self.updateSectionWidth
        )
        self.verticalHeader().sectionResized.connect(self.updateSectionHeight)
        self.horizontalScrollBar().valueChanged.connect(
            self.frozenTableView.horizontalScrollBar().setValue
        )
        self.frozenTableView.clicked.connect(self.deselectBase)
        self.clicked.connect(self.deselectFreeze)

    def getFrozenView(self):
        return self.frozenTableView

    def rowCount(self):
        return self.tm.rowCount()

    # Used for correctly matching column resizes
    def updateSectionWidth(self, logicalIndex, oldSize, newSize):
        self.setColumnWidth(logicalIndex, newSize)
        self.updateFrozenTableGeometry()

    # Used for correctly matching row resizes
    def updateSectionHeight(self, logicalIndex, oldSize, newSize):
        self.frozenTableView.setRowHeight(logicalIndex, newSize)
        self.updateFrozenTableGeometry()

    # Ensures that resizing the frozen table also resizes the base table
    def resizeEvent(self, event):
        QTableView.resizeEvent(self, event)
        self.updateFrozenTableGeometry()

    # Ensures that window and positional changes affect the frozen table
    def updateFrozenTableGeometry(self):
        self.frozenTableView.setGeometry(
            self.verticalHeader().width() + self.frameWidth(),
            self.frameWidth(),
            self.viewport().width(),
            self.rowHeight(0) + self.horizontalHeader().height(),
        )

    # Determines which table the mouse events are happening on
    def moveCursor(self, cursorAction, modifiers):
        current = QTableView.moveCursor(self, cursorAction, modifiers)
        return current

    def deselectBase(self):
        self.clearSelection()

    def deselectFreeze(self):
        self.frozenTableView.clearSelection()

    def sortIndicatorChanged(self, column, sortOrder):
        self.frozenTableView.horizontalHeader().setSortIndicatorShown(True)
        self.sortByColumn(column, sortOrder)
        self.horizontalHeader().setSortIndicator(column, sortOrder)
        self.parent.sortCatcher(sortOrder)
