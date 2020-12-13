"""
GUI to assist in the setup and running of an Opentrons OT-2.

Dennis Simpson
University of North Carolina at Chapel Hill
Lineberger Comprehensive Cancer Center
450 West Drive
Chapel Hill, NC  27599-7295

Copyright 2021
"""
import subprocess
import sys
import os
# from StringIO import StringIO

from UI_MainWindow import Ui_MainWindow
from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtWidgets import QApplication
# from PySide2.QtCore import QFile, QObject, QTimer, SIGNAL, QTime
from paramiko import SSHClient, AutoAddPolicy, RSAKey
from scp import SCPClient
import Tool_Box

__version__ = "0.1.1"
# pyside2-uic MainWindow.ui -o UI_MainWindow.py


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, obj=None, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setupUi(self)
        # Override the window label.
        self.label.setText("Gupta Lab Opentrons GUI v{}".format(__version__))

        self.tsv_file_select_btn.pressed.connect(self.transfer_tsv_file)
        self.closeGUI_btn.pressed.connect(self.exit_gui)
        self.simulate_run_btn.pressed.connect(self.simulate_run)

        self.select_program_combobx.addItems(["Generic_PCR_v0.1.0", "Illumina_Dual_Indexing"])
        self.selected_program = None
        self.select_program_combobx.currentTextChanged.connect(self.program_name)

        self.path_to_file = None

    @staticmethod
    def exit_gui():
        sys.exit()

    def program_name(self, s):
        self.selected_program = s

    def tr(self, text, **kwargs):
        return QtCore.QObject.tr(self, text)

    def select_file(self, source):
        self.path_to_file, _ = \
            QtWidgets.QFileDialog.getOpenFileName(self, self.tr(source),
                                                  self.tr("C:{0}Users{0}robotron{0}Documents{0}".format(os.sep)))

    def transfer_tsv_file(self):
        if not self.path_to_file:
            self.select_file("File Transfer Select")

        if self.path_to_file:
            # ToDo: get robot IP dynamically
            host_ip = '169.254.254.151'
            server_path = "/var/lib/jupyter/notebooks/ProcedureFile.tsv"

            # SCP will not overwrite or delete an existing file so we need to delete the server file first.
            ssh_client = SSHClient()
            ssh_client.load_system_host_keys()
            ssh_client.set_missing_host_key_policy(AutoAddPolicy())
            ssh_client.connect(hostname=host_ip, username='root', key_filename='C:{0}Users{0}robotron{0}ot2_ssh_key'.format(os.sep))

            # Check if file exists
            # ToDo: The remote exec command is not working.  Need to fix that!!!!!!!
            file_delete = False
            stdin, stdout, stderr = ssh_client.exec_command('stat {}'.format(server_path))
            # stdin, stdout, stderr = ssh_client.exec_command('ls '.format(server_path))

            if len(stdout.readlines()) > 0:
                file_delete = True
                stdin, stdout, stderr = ssh_client.exec_command('rm {}'.format(server_path))

            m = ""
            if len(stderr.readlines()) > 0 and file_delete:
                for line in stdout.readlines():
                    m += m + line

                self.error_report(m)
                stderr.close()
            elif len(stdout.readlines()) > 0 and file_delete:
                for line in stdout.readlines():
                    m += m + line
                self.success_report(m, "Deletion")

            # stdout.close()
            # stderr.close()
            # stdin.close()

            # Now transfer the new file to the robot.
            scp = SCPClient(ssh_client.get_transport())
            scp.put(files=self.path_to_file, remote_path=server_path, preserve_times=True)
            scp.close()
            ssh_client.close()

            upload_success = True
            if len(stdout.readlines()) > 0:
                upload_success = True

            if not upload_success:
                self.error_report("File Transfer Failed")
            elif upload_success:
                self.success_report("File Transferred Successfully", "File Transfer")



            """
            cmd = "scp -i ot2_ssh_key {} root@{}:{}".format(path_to_file, host_ip, server_path)
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            if proc.stderr:
                self.error_report(proc.stderr)
                # dlg = QtWidgets.QMessageBox(self)
                # dlg.setIcon(QtWidgets.QMessageBox.Critical)
                # dlg.setWindowTitle("Well, that didn't go so well.")
                # dlg.setText(proc.stderr.decode())
                # dlg.exec_()
            elif proc.stdout:
                self.success_report(proc.stdout, "Transfer Succeeded")

            """

    def simulate_run(self):
        # Todo: run simulation needs work
        if not self.selected_program:
            self.warning_report("Please Select Program for Simulation from dropdown list first.")
        # p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        m = "Now you did it.\n  Life is but a simulation and you are trying to simulate a simulation.\n  " \
            "This will cause reality to crash in on itself."

        self.run_simulation_output.insertPlainText(m)

    def error_report(self, message):
        QtWidgets.QMessageBox.critical(self, "Well, that didn't go so well.", message)

    def warning_report(self, message):
        QtWidgets.QMessageBox.warning(self, "You Forgot Something", message)

    def success_report(self, message, source):
        QtWidgets.QMessageBox.information(self, source, message)


def center_window(centralWidget):
    screen_geometry = QtGui.QGuiApplication.primaryScreen().availableGeometry()
    centralWidget.setWindowTitle("Opentrons Python Interface")
    centralWidget.resize(screen_geometry.width()*0.52, screen_geometry.height()*0.85)
    centralWidget.setGeometry(QtWidgets.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter,
                                                           centralWidget.size(), screen_geometry, ), )

if __name__ == "__main__":
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    center_window(window)
    window.show()
    sys.exit(app.exec_())
