from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6 import QtCore

PDF = 'file:///Users/digaspero/Documents/Development/omrexams/multipage.pdf'

class MarkdownView(QWebEngineView):
    """
    Webview for markdown
    """
    def __init__(self, widget):
        super().__init__(widget)
        self.settings().setAttribute(
            QWebEngineSettings.PluginsEnabled, True)
        self.settings().setAttribute(
            QWebEngineSettings.PdfViewerEnabled, True)
        self.load(QtCore.QUrl.fromUserInput(PDF))