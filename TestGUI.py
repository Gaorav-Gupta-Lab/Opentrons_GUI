import os
import subprocess
import sys
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtCore import QObject, QRectF
from PySide2.QtWidgets import QMainWindow, QFileDialog, QWidget, QVBoxLayout, QGraphicsScene, QGraphicsView, \
    QDesktopWidget, QApplication
from PySide2.QtGui import QPixmap


class Color(QWidget):
    def __init__(self, color):
        super().__init__()
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(color))
        self.setPalette(palette)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):

        self.centralWidget = QtWidgets.QWidget(MainWindow)

        # self.gridLayout = QtWidgets.QGridLayout(self.centralWidget)


        self.gridLayout = QtWidgets.QGridLayout()

        self.gridLayout.addWidget(self.centralWidget)

        window_label = QtWidgets.QLabel("This is our protocol upload")
        window_label.setParent(self.centralWidget)

        window_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        window_label_font = window_label.font()
        window_label_font.setPointSize(20)
        window_label.setFont(window_label_font)

        self.file_Select_Btn = QtWidgets.QPushButton()

        # self.file_Select_Btn = QtWidgets.QPushButton(self.centralWidget)
        # self.file_Select_Btn.setGeometry(QtCore.QRect(1082, 80, 121, 28))
        self.file_Select_Btn.setGeometry(QtCore.QRect(500, 200, 181, 41))
        self.file_Select_Btn.setObjectName("file_Select_Btn")
        self.file_Select_Btn.setText("Select Procedure File")

        self.simulate_run_btn = QtWidgets.QPushButton()
        self.simulate_run_btn.setGeometry(QtCore.QRect(380, 140, 181, 41))
        self.file_Select_Btn.setObjectName("simulate_run_btn")
        self.file_Select_Btn.setText("Simulate Protocol")
        #self.gridLayout.addWidget(self.file_Select_Btn)

        self.file_Select_Btn.setParent(self.centralWidget)
        self.simulate_run_btn.setParent(self.centralWidget)
        window_label.setParent(self.centralWidget)
        MainWindow.setCentralWidget(self.centralWidget)

        QtCore.QMetaObject.connectSlotsByName(MainWindow)


class CustomDialog(QtWidgets.QDialog):
    def __init__(self, dialog, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HELLO!")
        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout = QVBoxLayout()
        message = QtWidgets.QLabel(dialog)
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        Ui_MainWindow.__init__(self)

        # Initialize UI
        self.setupUi(self)

        self.file_Select_Btn.clicked.connect(self.file_transfer)

    def tr(self, text):
        return QObject.tr(self, text)

    def file_transfer(self):
        path_to_file, _ = QFileDialog.getOpenFileName(self, self.tr("Upload File"),
                                                      self.tr("C:{0}Users{0}dennis{0}Documents{0}".format(os.sep)))

        if path_to_file:
            cmd = "scp -i ot2_ssh_key {} root@169.254.48.252:/var/lib/jupyter/notebooks/ProcedureFile.tsv"\
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


        self.image_viewer = ImageViewer(path_to_file)
        # self.image_viewer.show()


class ImageViewer(QWidget):
    def __init__(self, image_path):
        super().__init__()

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

        self.load_image(image_path)

    def load_image(self, image_path):
        pixmap = QPixmap(image_path)
        self.scene.addPixmap(pixmap)
        self.view.fitInView(QRectF(0, 0, pixmap.width(), pixmap.height()), QtCore.Qt.KeepAspectRatio)
        self.scene.update()


def center_window(centralWidget):
    screen_geometry = QtGui.QGuiApplication.primaryScreen().availableGeometry()
    centralWidget.setWindowTitle("Opentrons Python Interface")
    centralWidget.resize(screen_geometry.width()*0.40, screen_geometry.height()*0.40)
    centralWidget.setGeometry(QtWidgets.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter,
                                                           centralWidget.size(), screen_geometry, ), )


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    main_window = MainWindow()
    main_window.show()
    center_window(main_window)
    # QtCore.QTimer.singleShot(0, lambda: center_window(main_window))
    sys.exit(app.exec_())
