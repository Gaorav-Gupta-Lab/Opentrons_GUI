"""
GUI to assist in the setup and running of an Opentrons OT-2.

Dennis Simpson
University of North Carolina at Chapel Hill
Lineberger Comprehensive Cancer Center
450 West Drive
Chapel Hill, NC  27599-7295

Copyright 2021
"""

import io
import shutil
import sys
import os
from TemplateErrorChecking import TemplateErrorChecking
from opentrons.simulate import simulate, format_runlog
from UI_MainWindow import Ui_MainWindow
from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtWidgets import QApplication
from paramiko import SSHClient, AutoAddPolicy
from contextlib import redirect_stdout
from scp import SCPClient

__version__ = "0.3.0"
# pyside2-uic MainWindow.ui -o UI_MainWindow.py


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setupUi(self)
        # Override the window label.
        self.label.setText("Gupta Lab Opentrons GUI v{}".format(__version__))
        self.path_to_tsv = None
        self.selected_program = None
        self.path_to_program = None
        self.program_error = True
        self.temp_tsv_path = "D:{}TempTSV.tsv".format(os.sep)
        self.tsv_file_select_btn.pressed.connect(self.select_file)
        self.closeGUI_btn.pressed.connect(self.exit_gui)
        self.simulate_run_btn.pressed.connect(self.simulate_run)
        self.select_program_combobx.addItems(["Generic PCR", "Illumina_Dual_Indexing"])
        self.select_program_combobx.currentTextChanged.connect(self.program_name)

    @staticmethod
    def exit_gui():
        sys.exit()

    def program_name(self, s):
        self.selected_program = s

    def tr(self, text, **kwargs):
        return QtCore.QObject.tr(self, text)

    def select_file(self):
        self.path_to_tsv, _ = \
            QtWidgets.QFileDialog.getOpenFileName(self, self.tr("File Select"),
                                                  self.tr("C:{0}Users{0}robotron{0}Documents{0}".format(os.sep)))

        shutil.copyfile(self.path_to_tsv, self.temp_tsv_path)

    def transfer_tsv_file(self):
        if not self.path_to_tsv:
            self.select_file()

        # ToDo: get robot IP dynamically
        host_ip = '169.254.254.151'
        server_path = "/var/lib/jupyter/notebooks/ProcedureFile.tsv"

        # SCP will not overwrite or delete an existing file so we need to delete the server file first.
        ssh_client = SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())
        try:
            ssh_client.connect(hostname=host_ip, username='root',
                               key_filename='C:{0}Users{0}robotron{0}ot2_ssh_key'.format(os.sep))
        except OSError:
            self.error_report("Unable to establish connection to robot for TSV file transfer.")
            return

        # Check if file exists
        # ToDo: The remote commands not working.  Need to fix that!!!!!!!
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

        # Now transfer the new file to the robot.
        scp = SCPClient(ssh_client.get_transport())
        scp.put(files=self.path_to_tsv, remote_path=server_path, preserve_times=True)
        scp.close()
        ssh_client.close()

        upload_success = True
        if len(stdout.readlines()) > 0:
            upload_success = True

        if not upload_success:
            self.error_report("File Transfer Failed")
        elif upload_success:
            self.success_report("File Transferred Successfully", "File Transfer")

    def simulate_run(self):
        # Todo: run simulation needs work
        if not self.selected_program:
            self.warning_report("Please Select Program for Simulation from dropdown list first.")

        # Redirect stdout and stderr here so they can be displayed in the GUI
        f = io.StringIO()
        with redirect_stdout(f):
            # Initialize template error checking
            template_error_check = TemplateErrorChecking(self.path_to_tsv)
            slot_error = template_error_check.slot_error_check()

            if slot_error:
                self.error_report("There is an error in the TSV Slot Definitions")
                return

            if self.selected_program == "Generic PCR":
                error_msg = template_error_check.generic_pcr()

                if error_msg:
                    self.error_report(error_msg)
                    return

        self.run_simulation_output.insertPlainText('{}'.format(f.getvalue()))
        self.path_to_program = "C:{0}Opentrons_Programs{0}Generic_PCR_v0.2.0.py".format(os.sep)
        self.run_simulation_output.insertPlainText('Begin Program Simulation.\n\tErrors stop program and are reported '
                                                   'in command window not GUI\n'.format(f.getvalue()))
        try:
            self.simulate_program()
        except:
            self.error_report("Simulation of {} Failed".format(os.path.basename(self.path_to_program)))
            return

        self.run_simulation_output.insertPlainText("\n")
        self.success_report("Simulations were successful.", "Simulation Module")
        os.remove(self.temp_tsv_path)
        self.transfer_tsv_file()

    def simulate_program(self):
        # Select program file if not located where we think it is.
        if not os.path.isfile(self.path_to_program):
            self.path_to_program, _ = \
                QtWidgets.QFileDialog.getOpenFileName(self, self.tr("Select Program File"),
                                                      self.tr("C:{0}Users{0}robotron{0}Documents{0}".format(os.sep)))
        protocol_file = open(self.path_to_program)

        labware_location = "{}/custom_labware".format(os.path.dirname(self.path_to_program), os.sep)
        run_log, __bundle__ = simulate(protocol_file, custom_labware_paths=[labware_location], propagate_logs=True)
        self.run_simulation_output.insertPlainText(format_runlog(run_log))

        protocol_file.close()

    def error_report(self, message):
        QtWidgets.QMessageBox.critical(self, "Well, that didn't go so well.", message)

    def warning_report(self, message):
        QtWidgets.QMessageBox.warning(self, "You Forgot Something", message)

    def success_report(self, message, source):
        QtWidgets.QMessageBox.information(self, source, message)


def center_window(central_widget):
    screen_geometry = QtGui.QGuiApplication.primaryScreen().availableGeometry()
    central_widget.setWindowTitle("Opentrons Python Interface")
    w_scale = 0.52
    h_scale = 0.8
    if screen_geometry.width() > 2000:
        w_scale = 0.27
    elif screen_geometry.width() < 1500:
        w_scale = 0.79
    if screen_geometry.height() > 1200:
        h_scale = 0.45
    print(screen_geometry.width(), screen_geometry.height())
    central_widget.resize(screen_geometry.width()*w_scale, screen_geometry.height()*h_scale)
    central_widget.setGeometry(QtWidgets.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter,
                                                            central_widget.size(), screen_geometry, ), )


if __name__ == "__main__":
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    center_window(window)
    window.show()
    sys.exit(app.exec_())
