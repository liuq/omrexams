"""
Main Window of the application.
"""

import wx
import wx.aui
from pubsub import pub
from pubsub.utils.notification import useNotifyByWriteFile
import sys
from . studentsgrid import StudentsGrid
from . questionseditor import QuestionsEditor
import gettext
_ = gettext.gettext

#useNotifyByWriteFile(sys.stdout)

from . models import *

class MainFrame(wx.Frame):
    """
    A Frame that says Hello World
    """

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super().__init__(*args, **kw)

        # create the models
        self.students = Students()
        self.questions = Questions()

        # create a panel in the frame
        panel = wx.Panel(self)
        self.notebook = wx.aui.AuiNotebook(panel, style=wx.BK_DEFAULT)

        self.grid = StudentsGrid(self.students, self.notebook)
        self.notebook.AddPage(self.grid, _("Students List"))
        self.editor = QuestionsEditor(self.questions, self.notebook)
        self.notebook.AddPage(self.editor, _("Question Editor"))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 5)
        panel.SetSizer(sizer)
        #self.Fit()

        # create a menu bar
        self.makeMenuBar()

        # and a status bar
        self.CreateStatusBar()
        self.SetStatusText(_("Welcome to OMR Exam"))

        pub.subscribe(self.file_status, "file")

    def file_status(self, status, file):
        self.SetStatusText("{} {}".format(status.capitalize(), file))

    def makeMenuBar(self):
        """
        A menu bar is composed of menus, which are composed of menu items.
        This method builds a set of menus and binds handlers to be called
        when the menu item is selected.
        """

        # Make a file menu with Hello and Exit items
        fileMenu = wx.Menu()
        openItem = fileMenu.Append(-1, _("File &Open") + _("\tCtrl-O"), _("Open Students' File"))
        self.Bind(wx.EVT_MENU, self.OnOpen, openItem)
        questionDirectoryItem = fileMenu.Append(-1, _("&Directory Open") + _("\tCtrl-D"), _("Open Questions' Directory"))        
        self.Bind(wx.EVT_MENU, self.OnDirectoryOpen, questionDirectoryItem)
        fileMenu.AppendSeparator()
        exitItem = fileMenu.Append(wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnExit,  exitItem)


        # Now a help menu for the about item
        helpMenu = wx.Menu()
        aboutItem = helpMenu.Append(wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)

        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, _("&File"))
        menuBar.Append(helpMenu, _("&Help"))

        self.SetMenuBar(menuBar)

    def OnOpen(self, event):
        with wx.FileDialog(self, _("Open Excel file"), wildcard=_("Excel files (*.xls[x])|*.xls;*.xlsx"),
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind
            self.students.load(fileDialog.GetPath())

    def OnDirectoryOpen(self, event):
        with wx.DirDialog(self, _("Open Directory"),
                           style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as dirDialog:
            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind
            self.questions.load_questions(dirDialog.GetPath())

    def OnExit(self, event):
        """Close the frame, terminating the application."""
        self.Close(True)

    def OnAbout(self, event):
        """Display an About Dialog"""
        wx.MessageBox(_("A simple OMR Exam generation"),
                      _("About OMR Exam"),
                      wx.OK | wx.ICON_INFORMATION)

import logging, logging.config

# TODO: move to app class
class MyApp(wx.App):
    def OnInit(self):
        self.logger = logging.getLogger(__name__)
        logging.config.fileConfig('logging.ini')
        return True

def start():
    # When this module is run (not imported) then create the app, the
    # frame, show it, and start the event loop.
    app = wx.App()
    app.SetAppName(_('OMR Exams'))
    app.logger = logging.getLogger('MyApp')
    app.logger.setLevel(logging.INFO)
    frm = MainFrame(None, title=_('OMR Exams'))
    frm.Show()
    app.MainLoop()