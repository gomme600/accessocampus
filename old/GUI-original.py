# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'GUI.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setEnabled(True)
        MainWindow.resize(800, 480)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.toolBox = QtWidgets.QToolBox(self.centralwidget)
        self.toolBox.setGeometry(QtCore.QRect(0, 0, 801, 421))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.toolBox.setFont(font)
        self.toolBox.setObjectName("toolBox")
        self.page = QtWidgets.QWidget()
        self.page.setGeometry(QtCore.QRect(0, 0, 801, 327))
        self.page.setObjectName("page")
        self.label_scannez_carte = QtWidgets.QLabel(self.page)
        self.label_scannez_carte.setGeometry(QtCore.QRect(70, 180, 661, 101))
        font = QtGui.QFont()
        font.setPointSize(40)
        self.label_scannez_carte.setFont(font)
        self.label_scannez_carte.setObjectName("label_scannez_carte")
        self.label_logo = QtWidgets.QLabel(self.page)
        self.label_logo.setGeometry(QtCore.QRect(0, 0, 801, 171))
        self.label_logo.setText("")
        self.label_logo.setPixmap(QtGui.QPixmap(":/images/accessocampus_ressources/neocampus_logo.png"))
        self.label_logo.setScaledContents(True)
        self.label_logo.setObjectName("label_logo")
        self.toolBox.addItem(self.page, "")
        self.page_2 = QtWidgets.QWidget()
        self.page_2.setGeometry(QtCore.QRect(0, 0, 801, 327))
        self.page_2.setObjectName("page_2")
        self.label_code_acces = QtWidgets.QLabel(self.page_2)
        self.label_code_acces.setGeometry(QtCore.QRect(160, 10, 481, 71))
        font = QtGui.QFont()
        font.setPointSize(40)
        self.label_code_acces.setFont(font)
        self.label_code_acces.setObjectName("label_code_acces")
        self.horizontalLayoutWidget = QtWidgets.QWidget(self.page_2)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(120, 80, 541, 61))
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pushButton_dig_1 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_dig_1.setObjectName("pushButton_dig_1")
        self.horizontalLayout.addWidget(self.pushButton_dig_1)
        self.pushButton_dig_2 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_dig_2.setObjectName("pushButton_dig_2")
        self.horizontalLayout.addWidget(self.pushButton_dig_2)
        self.pushButton_dig_3 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_dig_3.setObjectName("pushButton_dig_3")
        self.horizontalLayout.addWidget(self.pushButton_dig_3)
        self.pushButton_dig_4 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_dig_4.setObjectName("pushButton_dig_4")
        self.horizontalLayout.addWidget(self.pushButton_dig_4)
        self.pushButton_dig_5 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_dig_5.setObjectName("pushButton_dig_5")
        self.horizontalLayout.addWidget(self.pushButton_dig_5)
        self.horizontalLayoutWidget_2 = QtWidgets.QWidget(self.page_2)
        self.horizontalLayoutWidget_2.setGeometry(QtCore.QRect(120, 150, 541, 61))
        self.horizontalLayoutWidget_2.setObjectName("horizontalLayoutWidget_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_2)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pushButton_dig_6 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.pushButton_dig_6.setObjectName("pushButton_dig_6")
        self.horizontalLayout_2.addWidget(self.pushButton_dig_6)
        self.pushButton_dig_7 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.pushButton_dig_7.setObjectName("pushButton_dig_7")
        self.horizontalLayout_2.addWidget(self.pushButton_dig_7)
        self.pushButton_dig_8 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.pushButton_dig_8.setObjectName("pushButton_dig_8")
        self.horizontalLayout_2.addWidget(self.pushButton_dig_8)
        self.pushButton_dig_9 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.pushButton_dig_9.setObjectName("pushButton_dig_9")
        self.horizontalLayout_2.addWidget(self.pushButton_dig_9)
        self.pushButton_dig_0 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.pushButton_dig_0.setObjectName("pushButton_dig_0")
        self.horizontalLayout_2.addWidget(self.pushButton_dig_0)
        self.pushButton_dig_val = QtWidgets.QPushButton(self.page_2)
        self.pushButton_dig_val.setGeometry(QtCore.QRect(270, 220, 121, 61))
        self.pushButton_dig_val.setObjectName("pushButton_dig_val")
        self.pushButton_dig_val_2 = QtWidgets.QPushButton(self.page_2)
        self.pushButton_dig_val_2.setGeometry(QtCore.QRect(400, 220, 121, 61))
        self.pushButton_dig_val_2.setObjectName("pushButton_dig_val_2")
        self.toolBox.addItem(self.page_2, "")
        self.label_statut_porte = QtWidgets.QLabel(self.centralwidget)
        self.label_statut_porte.setGeometry(QtCore.QRect(300, 430, 211, 31))
        font = QtGui.QFont()
        font.setPointSize(25)
        self.label_statut_porte.setFont(font)
        self.label_statut_porte.setObjectName("label_statut_porte")
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        self.toolBox.setCurrentIndex(0)
        self.toolBox.layout().setSpacing(6)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Accessocampus"))
        self.label_scannez_carte.setText(_translate("MainWindow", "Scannez votre carte d\'acces"))
        self.toolBox.setItemText(self.toolBox.indexOf(self.page), _translate("MainWindow", "NFC"))
        self.label_code_acces.setText(_translate("MainWindow", "Entrez Code d\'acces"))
        self.pushButton_dig_1.setText(_translate("MainWindow", "1"))
        self.pushButton_dig_2.setText(_translate("MainWindow", "2"))
        self.pushButton_dig_3.setText(_translate("MainWindow", "3"))
        self.pushButton_dig_4.setText(_translate("MainWindow", "4"))
        self.pushButton_dig_5.setText(_translate("MainWindow", "5"))
        self.pushButton_dig_6.setText(_translate("MainWindow", "6"))
        self.pushButton_dig_7.setText(_translate("MainWindow", "7"))
        self.pushButton_dig_8.setText(_translate("MainWindow", "8"))
        self.pushButton_dig_9.setText(_translate("MainWindow", "9"))
        self.pushButton_dig_0.setText(_translate("MainWindow", "0"))
        self.pushButton_dig_val.setText(_translate("MainWindow", "Valider"))
        self.pushButton_dig_val_2.setText(_translate("MainWindow", "Annuler"))
        self.toolBox.setItemText(self.toolBox.indexOf(self.page_2), _translate("MainWindow", "Code"))
        self.label_statut_porte.setText(_translate("MainWindow", "Porte fermée"))

import accessocampus_GUI_rc

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
