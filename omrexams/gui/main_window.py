from __future__ import annotations
from PySide6.QtCore import QCoreApplication, Signal, Slot, Qt, QObject, QEvent, QByteArray, QTimer
from PySide6 import QtWidgets
from PySide6.QtGui import QAction, QActionGroup, QPixmap, QImage

from omrexams.gui._ui.main_window_ui import Ui_MainWindow

from typing import List, Tuple
import json
import os
from functools import partial
import io
from itertools import combinations
from markdown import Markdown

class MainWindow(QtWidgets.QMainWindow):
    """Main Window of the application."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.markdowner = Markdown(extensions=['markdown_checklist.extension', 'md4mathjax'])
        self.debounce = QTimer()
        self.debounce.setInterval(500)
        self.debounce.setSingleShot(True)
        self.debounce.timeout.connect(self.update_markdown)

        self.ui.plainTextEdit.textChanged.connect(self.debounce.start)

        # self.ui.action_quit.triggered.connect(self.close_app)
        # self.ui.action_quit.setShortcutContext(Qt.ApplicationShortcut)
        # self.ui.action_close.triggered.connect(self.close_window)
        # self.ui.action_open.triggered.connect(self.open_file)
        # self.ui.action_run.triggered.connect(self.run_solver)
        # self.ui.action_minimize.triggered.connect(self.minimize_window)
        # self.ui.action_run.setDisabled(True)   

    # Needed for https://bugreports.qt.io/browse/PYSIDE-131
    # Resolved in Qt6, but it could be a tiny bit faster than tr()
    def __tr(self, txt, disambiguation=None, n=-1):
        return QCoreApplication.translate("MainWindow", txt, disambiguation, n)

    def update_markdown(self):
        content = """<!doctype html>
        <html>
          <head>
          </head>
          <body>
        """
        content += self.markdowner.convert(self.ui.plainTextEdit.toPlainText())
        content += "</body></html>"
        self.ui.widget.setHtml(content)