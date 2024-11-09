"""
This file contains the main script, which is the application entry point.
It is named like this for overriding the app name when called withing python (see Mac OS menus).
"""

import sys
import argparse

from PySide6 import QtGui, QtCore, QtWidgets
from PySide6.QtWidgets import QApplication

import time

from .main_window import MainWindow

from ._ui import resources_rc  # noqa

def main_ui():
    parser = argparse.ArgumentParser(description='Runs the OMRexams GUI')
    parser.add_argument('--quick', '-q', action='store_true')
    args, unknownargs = parser.parse_known_args()
    app = QApplication(unknownargs)
    #app.setWindowIcon(QtGui.QIcon(':/icons/safe_dss.png'))

    # Create splashscreen
    # if QtGui.QScreen.devicePixelRatio(QtWidgets.QApplication.primaryScreen()) < 2:        
    #     splash_pix = QtGui.QPixmap(':/images/splash.png').scaledToWidth(640)
    # else:
    #     splash_pix = QtGui.QPixmap(':/images/splash@2x.png').scaledToWidth(1280)
    # splash = QtWidgets.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    # # add fade to splashscreen 
    # splash.show()
    app.processEvents()

    # splash.showMessage(QtCore.QCoreApplication.translate("Splash", u"Loading fonts...", None), QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft)
    # # QFontDatabase.addApplicationFont(':/fonts/Roboto-Regular.ttf')
    # # app.setFont(QFont('Roboto'))
    # app.processEvents()
    # if not args.quick:
    #     time.sleep(0.5)

    # splash.showMessage(QtCore.QCoreApplication.translate("Splash", u"Loading styles...", None), QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft)
    # # f = QFile(':/style.qss')
    # # f.open(QFile.ReadOnly | QFile.Text)
    # # app.setStyleSheet(QTextStream(f).readAll())
    # # f.close()
    # app.processEvents()

    # splash.showMessage(QtCore.QCoreApplication.translate("Splash", u"Loading translations...", None), QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft)
    # app.processEvents()
    # translator = QtCore.QTranslator()
    # translator.load(':/translations/' + QtCore.QLocale.system().name() + '.qm')
    # app.installTranslator(translator)
    # if not args.quick:
    #     time.sleep(0.5)

    # splash.showMessage(QtCore.QCoreApplication.translate("Splash", u"Preparing inference engine...", None), QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft)
    # app.processEvents()
    # # TODO: prepare the CLINGO inference engine
    # if not args.quick:
    #     time.sleep(2)

    # splash.showMessage(QtCore.QCoreApplication.translate("Splash", "Ready", None), QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft)
    # app.processEvents()
    # if not args.quick:
    #     time.sleep(1.5)
    
    mw = MainWindow()
#    splash.finish(mw)
    mw.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main_ui()
