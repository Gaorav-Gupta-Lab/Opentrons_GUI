# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MainWindow.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1040, 871)
        font = QFont()
        font.setPointSize(18)
        MainWindow.setFont(font)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.centralwidget.setFont(font)
        self.tsv_file_select_btn = QPushButton(self.centralwidget)
        self.tsv_file_select_btn.setObjectName(u"tsv_file_select_btn")
        self.tsv_file_select_btn.setGeometry(QRect(280, 80, 451, 51))
        self.tsv_file_select_btn.setFont(font)
        self.tsv_file_select_btn.setCheckable(True)
        self.tsv_file_select_btn.setAutoRepeatDelay(302)
        self.tsv_file_select_btn.setAutoDefault(True)
        self.tsv_file_select_btn.setFlat(False)
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        self.label.setEnabled(True)
        self.label.setGeometry(QRect(59, 9, 911, 51))
        font1 = QFont()
        font1.setFamily(u"Comic Sans MS")
        font1.setPointSize(22)
        self.label.setFont(font1)
        self.label.setFrameShape(QFrame.Box)
        self.label.setAlignment(Qt.AlignCenter)

        self.closeGUI_btn = QPushButton(self.centralwidget)
        self.closeGUI_btn.setObjectName(u"closeGUI_btn")
        self.closeGUI_btn.setGeometry(QRect(310, 700, 351, 81))
        self.closeGUI_btn.setAutoDefault(True)
        self.simulate_run_btn = QPushButton(self.centralwidget)
        self.simulate_run_btn.setObjectName(u"simulate_run_btn")
        self.simulate_run_btn.setGeometry(QRect(281, 250, 451, 51))
        self.simulate_run_btn.setAutoDefault(True)
        self.run_simulation_output = QTextBrowser(self.centralwidget)
        self.run_simulation_output.setObjectName(u"run_simulation_output")
        self.run_simulation_output.setGeometry(QRect(31, 420, 971, 251))
        font2 = QFont()
        font2.setFamily(u"Arial")
        font2.setPointSize(10)
        self.run_simulation_output.setFont(font2)
        self.select_program_combobx = QComboBox(self.centralwidget)
        self.select_program_combobx.setObjectName(u"select_program_combobx")
        self.select_program_combobx.setGeometry(QRect(281, 180, 451, 51))
        self.select_program_label = QLabel(self.centralwidget)
        self.select_program_label.setObjectName(u"select_program_label")
        self.select_program_label.setGeometry(QRect(280, 150, 451, 31))
        font3 = QFont()
        font3.setPointSize(14)
        self.select_program_label.setFont(font3)
        self.run_ot2 = QPushButton(self.centralwidget)
        self.run_ot2.setObjectName(u"run_ot2")
        self.run_ot2.setGeometry(QRect(30, 340, 451, 51))
        self.run_ot2.setAutoDefault(True)
        self.cancel_run_btn = QPushButton(self.centralwidget)
        self.cancel_run_btn.setObjectName(u"cancel_run_btn")
        self.cancel_run_btn.setGeometry(QRect(550, 340, 451, 51))
        self.cancel_run_btn.setContextMenuPolicy(Qt.NoContextMenu)
        self.cancel_run_btn.setAutoFillBackground(True)
        self.cancel_run_btn.setAutoDefault(True)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1040, 38))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        self.tsv_file_select_btn.setDefault(True)
        self.closeGUI_btn.setDefault(True)
        self.simulate_run_btn.setDefault(True)
        self.run_ot2.setDefault(True)
        self.cancel_run_btn.setDefault(True)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.tsv_file_select_btn.setText(QCoreApplication.translate("MainWindow", u"Select TSV File", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Gupta Lab Opentrons GUI v0.1.0", None))
        self.closeGUI_btn.setText(QCoreApplication.translate("MainWindow", u"Close GUI", None))
        self.simulate_run_btn.setText(QCoreApplication.translate("MainWindow", u"Simulate Run", None))
        self.run_simulation_output.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Program Output", None))
        self.select_program_combobx.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Select Program to Simulate", None))
        self.select_program_label.setText(QCoreApplication.translate("MainWindow", u"Select Program for Simulation:", None))
        self.run_ot2.setText(QCoreApplication.translate("MainWindow", u"Run OT-2", None))
        self.cancel_run_btn.setText(QCoreApplication.translate("MainWindow", u"Cancel OT-2 Run", None))
    # retranslateUi

