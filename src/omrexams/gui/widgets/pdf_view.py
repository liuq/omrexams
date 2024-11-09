from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6 import QtCore
import pathlib

PDF =  (pathlib.Path(__file__).parent / '../../multipage.pdf').resolve()
PDFJS = (pathlib.Path(__file__).parent / '../resources/pdfjs/web/viewer.html').resolve()

class PdfView(QWebEngineView):
    """
    Webview for pdf file using pdfjs
    """
    def __init__(self, widget):
        super().__init__(widget)        
        self.load(QtCore.QUrl.fromUserInput(f"file://{PDFJS}?file=file://{PDF}"))

    def set_page(self, page : int):
        self.page().runJavaScript(f'PDFViewerApplication && PDFViewerApplication.pdfViewer.currentPageNumber = {page};')