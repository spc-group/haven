from PyQt5.QtWidgets import QFileDialog, QLineEdit


class FileBrowser:
    @classmethod
    def browse(cls, fileLineEdit: QLineEdit, nameFilter=None, directoryOnly=False):
        """Displays the file system for the user to navigate and
        sets the text of the give line edit to be the name of the selected file"""
        fileBrowserDialog = QFileDialog()
        fileBrowserDialog.setOption(QFileDialog.DontUseNativeDialog, True)
        fileBrowserDialog.setNameFilter(nameFilter)
        if directoryOnly:
            fileBrowserDialog.setFileMode(QFileDialog.Directory)
            fileBrowserDialog.setOption(QFileDialog.ShowDirsOnly)
        if fileBrowserDialog.exec_():
            file = fileBrowserDialog.selectedFiles()[0]
            # Data text field text changed event will take over.
            fileLineEdit.setText(file)
