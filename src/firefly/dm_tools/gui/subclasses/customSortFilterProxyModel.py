#!/usr/bin/env python

from PyQt5.QtCore import QRegExp, QSortFilterProxyModel, Qt


class CustomSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(CustomSortFilterProxyModel, self).__init__(parent)
        self.badgeRegExp = QRegExp()
        self.firstRegExp = QRegExp()
        self.lastRegExp = QRegExp()
        self.emailRegExp = QRegExp()

    def setUsernameFilter(self, text):
        self.badgeRegExp = QRegExp(text, Qt.CaseInsensitive, QRegExp.FixedString)
        self.invalidateFilter()

    def setFirstFilter(self, text):
        self.firstRegExp = QRegExp(text, Qt.CaseInsensitive, QRegExp.FixedString)
        self.invalidateFilter()

    def setLastFilter(self, text):
        self.lastRegExp = QRegExp(text, Qt.CaseInsensitive, QRegExp.FixedString)
        self.invalidateFilter()

    def setEmailFilter(self, text):
        self.emailRegExp = QRegExp(text, Qt.CaseInsensitive, QRegExp.FixedString)
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        if row == 0:
            return True
        else:
            sourceModel = self.sourceModel()
            badgeIndex = sourceModel.index(row, 0, parent)
            badge = str(sourceModel.data(badgeIndex))
            firstIndex = sourceModel.index(row, 1, parent)
            first = str(sourceModel.data(firstIndex)).lower()
            lastIndex = sourceModel.index(row, 2, parent)
            last = str(sourceModel.data(lastIndex)).lower()
            emailIndex = sourceModel.index(row, 3, parent)
            email = str(sourceModel.data(emailIndex)).lower()
            return (
                str(self.badgeRegExp.pattern()) in badge
                and str(self.firstRegExp.pattern()) in first
                and str(self.lastRegExp.pattern()) in last
                and str(self.emailRegExp.pattern()) in email
            ) or str(badge) == ""
