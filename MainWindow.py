#!python
import subprocess
import sys
import os
from PySide2.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QLabel, QLineEdit, QFileDialog
from PySide2 import QtWidgets
from PySide2.QtCore import QFile, Qt, QObject
from PySide2.QtUiTools import QUiLoader, loadUiType
import Tool_Box


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        # super().__init__(*args, **kwargs, parent=None)
        self.loader = QUiLoader()

        # self.user_name = self.window.findChild(QLineEdit, 'UserName')
        # self.btn = self.window.findChild(QPushButton, 'Button1')
        #self.left_pipette_cb = self.window.findChild(QtWidgets.QComboBox, 'LeftPipette')
        #self.right_pipette_cb = self.window.findChild(QtWidgets.QComboBox, 'RightPipette')
        #self.slot1_cb = self.window.findChild(QtWidgets.QComboBox, 'slot1ComboBox')
        #self.slot2_cb = self.window.findChild(QtWidgets.QComboBox, 'slot2ComboBox')
        self.file_select_button = self.window.findChild(QPushButton, "file_select_btn")


        self.load_ui()

    def load_ui(self):
        path = os.path.join(os.path.dirname(__file__), "MainWindow.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.window = self.loader.load(ui_file, self)
        ui_file.close()
        # self.window.show()
        # btn = self.window.findChild(QPushButton, 'Button1')
        self.file_select_button.clicked.connect(self.the_button_was_clicked)
        # sys.exit(app.exec_())

    def the_button_was_clicked(self):
        path_to_file, _ = QFileDialog.getOpenFileName(self, self.tr("Upload File"),
                                                      self.tr("C:{0}Users{0}dennis{0}Documents{0}".format(os.sep)))

        if path_to_file:
            cmd = "scp -i ot2_ssh_key {} root@169.254.48.252:/var/lib/jupyter/notebooks/ProcedureFile.tsv" \
                .format(path_to_file)
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            print("CMD:  ", cmd)
            print(proc.stdout.decode())
            if proc.stderr:
                # dlg = QtWidgets.QMessageBox(self)
                QtWidgets.QMessageBox.critical(self, "Well, that didn't go so well.", proc.stderr.decode())
                # dlg.setIcon(QtWidgets.QMessageBox.Critical)
                # dlg.setWindowTitle("Well, that didn't go so well.")
                # dlg.setText(proc.stderr.decode())
                # dlg.exec_()
            elif proc.stdout:
                QtWidgets.QMessageBox.information(self, "Transfer Succeeded", proc.stdout.decode())

    def tr(self, text):
        return QObject.tr(self, text)


if __name__ == "__main__":
    app = QApplication([])  # This is our main application instance
    app.setStyle("windows")
    main_window = MainWindow()  # This is our main window
    main_window.show()
    sys.exit(app.exec_())  # shut it all down
