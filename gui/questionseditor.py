import wx
import wx.stc
import wx.html2
from pubsub import pub
import logging
import gettext
from mistletoe import Document
from . utils.markdown import CheckmarkRenderer
_ = gettext.gettext

class QuestionsEditor(wx.Panel):
    def __init__(self, questions, *args, **kwargs):
        super(QuestionsEditor, self).__init__(*args, **kwargs)
        self.logger = wx.GetApp().logger
        self.questions = questions
        self.questions_ctrl = wx.TreeCtrl(self)
#        self.editor = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE)         
        self.editor = wx.stc.StyledTextCtrl(self)
        self.editor.SetLexer(wx.stc.STC_LEX_MARKDOWN)
        self.editor.SetAutoLayout(True)
        
        self.viewer = wx.html2.WebView.New(self) 

        # layout      
        sizer = wx.FlexGridSizer(2, 3, 5, 5)
        sizer.AddGrowableCol(0, 1)
        sizer.AddGrowableCol(1, 1)
        sizer.AddGrowableCol(2, 1)
        sizer.AddGrowableRow(0)
        sizer.AddGrowableRow(1)
        sizer.Add(self.questions_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.editor, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.viewer, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer)

        # notifications and events
        pub.subscribe(self.loaded, 'questions.load.loaded')
        self.questions_ctrl.Bind(wx.EVT_TREE_SEL_CHANGED, self.selection)

    def loaded(self, number):
        self.questions_ctrl.DeleteAllItems()
        root = self.questions_ctrl.AddRoot(self.questions.configuration['config'])
        self.questions_ctrl.SetItemData(root, { 'content': [self.questions.exam_header] })
        for q in self.questions.questions:
            item = self.questions_ctrl.AppendItem(root, q['filename'])
            self.questions_ctrl.SetItemData(item, q)
        self.questions_ctrl.ExpandAllChildren(root)
        self.selection(None)

    def selection(self, event):        
        selected = self.questions_ctrl.GetSelection()
        q = self.questions_ctrl.GetItemData(selected)
        print(q)
        content = '\n\n---\n\n'.join(q['content'])
        self.editor.SetText(content)
        with CheckmarkRenderer() as renderer:
            html = renderer.render(Document(content))
        self.viewer.SetPage(html, "")
