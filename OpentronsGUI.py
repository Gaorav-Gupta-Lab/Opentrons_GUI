"""
GUI to assist in the setup and running of an Opentrons OT-2.

Dennis Simpson
University of North Carolina at Chapel Hill
Lineberger Comprehensive Cancer Center
450 West Drive
Chapel Hill, NC  27599-7295

Copyright 2021
"""
import datetime
import io
import shutil
import sys
import os
import socket
from TemplateErrorChecking import TemplateErrorChecking
from opentrons.simulate import simulate, format_runlog
from UI_MainWindow import Ui_MainWindow
from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtWidgets import QApplication
from paramiko import SSHClient, AutoAddPolicy
from contextlib import redirect_stdout, suppress
from scp import SCPClient
# import Tool_Box


__version__ = "1.0.1"
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
        self.critical_error = False
        self.server_path = "/var/lib/jupyter/notebooks/"
        self.server_tsv_file = "ProcedureFile.tsv"
        self.temp_tsv_path = "C:{0}Users{0}{1}{0}Documents{0}TempTSV.tsv".format(os.sep, os.getlogin())
        self.ssh_client = None
        self.tsv_file_select_btn.pressed.connect(self.select_file)
        self.closeGUI_btn.pressed.connect(self.exit_gui)
        self.simulate_run_btn.pressed.connect(self.simulate_run)
        self.select_program_combobx.addItems(["ddPCR", "Generic PCR", "Illumina_Dual_Indexing"])
        self.select_program_combobx.currentTextChanged.connect(self.program_name)
        self.cancel_run_btn.pressed.connect(self.cancel_run)
        self.run_ot2.pressed.connect(self.run_program)

    def run_program(self):
        self.warning_report("This Feature is Not Yet Implemented")
        return
        program_name = os.path.basename(self.path_to_program)
        cmd = "opentrons_execute {0}{1} -L {0}custom_labware".format(self.server_path, program_name)
        print(cmd)

        self.ssh_client.get_transport()
        self.ssh_client.invoke_shell()
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        print("After run")
        stdout.channel.recv_exit_status()
        stderr.channel.recv_exit_status()
        response = stdout.readlines()
        er = stderr.readlines()
        for line in er:
            print("error: ", line)
        for line in response:
            print("response line:  ", line)

    def cancel_run(self):
        self.warning_report("This Feature is Not Yet Implemented")
        return
        stdin, stdout, stderr = self.ssh_client.send("\x03")
        stdout.channel.recv_exit_status()
        response = stdout.readlines()
        for line in response:
            print(line)

    def exit_gui(self):
        with suppress(AttributeError):
            self.ssh_client.close()
        sys.exit()

    def program_name(self, s):
        self.selected_program = s

    def tr(self, text, **kwargs):
        return QtCore.QObject.tr(self, text)

    def select_file(self):
        self.path_to_tsv, _ = \
            QtWidgets.QFileDialog.getOpenFileName(self, self.tr("File Select"),
                                                  self.tr("C:{0}Users{0}{1}{0}Documents{0}".
                                                          format(os.sep, os.getlogin())))
        if self.path_to_tsv:
            shutil.copyfile(self.path_to_tsv, self.temp_tsv_path)
        else:
            self.warning_report("TSV File Not Selected.")

    def connect_to_ot2(self):
        """
        Establish SSH connection to robot.
        :return:
        """
        robot_name = "OT2CEP20180915A20"
        try:
            host_ip = socket.gethostbyname(robot_name)
        except socket.gaierror:
            self.error_report("Unable to connect to Opentrons OT-2 {}\n Is robot on and connected to computer?"
                              .format(robot_name))
            return

        ssh_client = SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())
        try:
            ssh_client.connect(hostname=host_ip, username='root',
                               key_filename='C:{0}Users{0}robotron{0}ot2_ssh_key'.format(os.sep))
        except OSError:
            self.error_report("SSH unable to establish connection to robot.  Secure Key error")
            self.critical_error = True
            raise SystemExit(1)

        return ssh_client

    def transfer_tsv_file(self):
        """
        If everything checks out then transfer the files to the robot.
        :rtype: object
        :return:
        """

        # Establish a connection to the robot.
        self.ssh_client = self.connect_to_ot2()

        # If communications with the OT-2 cannot be established then let the user know.  This might be an expected 
        # behavior.
        if not self.ssh_client:
            self.warning_report("Communications with OT-2 not established.  If this was expected then you can safely "
                                "ignore this message")
            return

        # If we have a critical error then don't do anything else.
        if self.critical_error:
            return

        if not self.path_to_tsv:
            self.select_file()

        # program_path = os.path.dirname(self.path_to_program)
        # program_name = os.path.basename(self.path_to_program)

        # Initialize scp and transfer the files to the robot.
        scp = SCPClient(self.ssh_client.get_transport())
        # TSF file transfer
        scp.put(files=self.path_to_tsv, remote_path="{}{}".format(self.server_path, self.server_tsv_file),
                preserve_times=True)

        # Program file transfer
        # scp.put(files=self.path_to_program, remote_path=self.server_path, preserve_times=True)

        # Confirm files have transferred.
        cmd = "ls {}".format(self.server_path)
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        stdout.channel.recv_exit_status()
        response = stdout.readlines()
        transferred_files = []

        for line in response:
            transferred_files.append(line.strip("\n"))

        if self.server_tsv_file not in transferred_files:
            self.error_report("TSV File Transfer Failed")
            self.critical_error = True
            # elif program_name not in transferred_files:
            # self.error_report("Program File {} Transfer Failed".format(program_name))
            # self.critical_error = True
        else:
            self.success_report("All Files Transferred Successfully", "File Transfer")

        scp.close()

    def simulate_run(self):
        """
        This will check the ProcedureTSV file for syntax errors.
        :return:
        """

        # If we have a critical error then don't do anything else.
        if self.critical_error:
            return

        if not self.selected_program:
            self.warning_report("Please Select Program for Simulation from dropdown list first.")

        # Redirect stdout and stderr so they can be displayed in the GUI
        f = io.StringIO()

        template_error_check = TemplateErrorChecking(self.path_to_tsv)
        '''
        # Debugging code block
        slot_error = template_error_check.slot_error_check()
        pipette_error = template_error_check.pipette_error_check()
        tip_box_error = template_error_check.tip_box_error_check()
        error_msg = template_error_check.droplet_pcr()
        Tool_Box.debug_messenger(error_msg)
        '''
        with redirect_stdout(f):
            # Initialize template error checking
            value_error = template_error_check.parameter_checks()
            if value_error:
                self.error_report(value_error)
                return

            slot_error = template_error_check.slot_error_check()

            if slot_error:
                self.error_report(slot_error)
                return

            pipette_error = template_error_check.pipette_error_check()
            if pipette_error:
                self.error_report(pipette_error)
                return

            tip_box_error = template_error_check.tip_box_error_check()
            if tip_box_error:
                self.error_report(tip_box_error)
                return

            if self.selected_program == "Generic PCR" or self.selected_program == "ddPCR":
                error_msg = template_error_check.pcr_check(self.selected_program)

            elif self.selected_program == "Illumina_Dual_Indexing":
                error_msg = template_error_check.illumina_dual_indexing(self.selected_program)

            else:
                error_msg = "Somehow you have selected a program that does not exist.\nConsult the code admin."

            if error_msg:
                self.error_report(error_msg)
                return

        self.run_simulation_output.insertPlainText('{}'.format(f.getvalue()))
        if self.selected_program == "Generic PCR":
            # self.path_to_program = "C:{0}Opentrons_Programs{0}Generic_PCR.py".format(os.sep)
            self.path_to_program = "C:{0}Opentrons_Programs{0}PCR.py".format(os.sep)

        elif self.selected_program == "Illumina_Dual_Indexing":
            self.path_to_program = "C:{0}Opentrons_Programs{0}Illumina_Dual_Indexing.py".format(os.sep)

        elif self.selected_program == "ddPCR":
            # self.path_to_program = "C:{0}Opentrons_Programs{0}ddPCR.py".format(os.sep)
            self.path_to_program = "C:{0}Opentrons_Programs{0}PCR.py".format(os.sep)

        self.run_simulation_output.insertPlainText('Begin Program Simulation.\n'.format(f.getvalue()))
        self.simulate_program()

        self.run_simulation_output.insertPlainText("\n")
        self.success_report("Simulations were successful.", "Simulation Module")
        self.transfer_tsv_file()
        os.remove(self.temp_tsv_path)

    def simulate_program(self):
        """
        This will run an Opentrons simulation on the program.
        """

        # If we have a critical error then don't do anything else.
        if self.critical_error:
            return

        # Select program file if not located where we think it is.
        if not os.path.isfile(self.path_to_program):
            self.path_to_program, _ = \
                QtWidgets.QFileDialog.getOpenFileName(self, self.tr("Select Program File"),
                                                      self.tr("C:{0}Users{0}{1}{0}Documents{0}"
                                                              .format(os.sep, os.getlogin())))

        self.info_report('If you do not get a "Success" notice then the simulation failed.\nSee the terminal window '
                         'for the reason')

        protocol_file = open(self.path_to_program)
        labware_location = "{}{}custom_labware".format(os.path.dirname(self.path_to_program), os.sep)
        run_log, __bundle__ = simulate(protocol_file, custom_labware_paths=[labware_location], propagate_logs=False)

        # Write the simulation steps to a file
        simulation_date = datetime.datetime.today().strftime("%a %b %d %H:%M %Y")
        outfile = open("C:{0}Users{0}{1}{0}Documents{0}{2}_Simulation.txt"
                       .format(os.sep, os.getlogin(), self.selected_program), 'w', encoding="UTF-16")
        step_number = 1
        t = format_runlog(run_log).split("\n")
        outstring = "Opentrons OT-2 Steps.\nDate:  {}\nProgram File: {}\nTSV File:  {}\n\nStep\tCommand\n"\
                    .format(simulation_date, self.selected_program, self.path_to_tsv)

        for line in t:
            outstring += "{}\t{}\n".format(step_number, line)
            step_number += 1
        outfile.write(outstring)
        outfile.close()

        # Write the simulation steps to the GUI
        self.run_simulation_output.insertPlainText(format_runlog(run_log))

        protocol_file.close()

    def info_report(self, message):
        QtWidgets.QMessageBox.information(self, "Take Heed", message)

    def error_report(self, message):
        QtWidgets.QMessageBox.critical(self, "Well, that didn't go so well.", message)

    def warning_report(self, message):
        QtWidgets.QMessageBox.warning(self, "You Sure You Want To Continue?", message)

    def success_report(self, message, source):
        QtWidgets.QMessageBox.information(self, source, message)


def center_window(central_widget):
    screen_geometry = QtGui.QGuiApplication.primaryScreen().availableGeometry()
    central_widget.setWindowTitle("Opentrons Python Interface")
    w_scale = 0.55
    h_scale = 0.85
    if screen_geometry.width() > 2000:
        w_scale = 0.27
    elif screen_geometry.width() < 1500:
        w_scale = 0.79
    if screen_geometry.height() > 1200:
        h_scale = 0.45
    # print(screen_geometry.width(), screen_geometry.height())
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
