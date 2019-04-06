import wx
import wx.grid as gridlib
from pubsub import pub
import logging
import gettext
_ = gettext.gettext

class StudentsGrid(gridlib.Grid):
    def __init__(self, students, *args, **kwargs):
        super(StudentsGrid, self).__init__(*args, **kwargs)
        self.logger = wx.GetApp().logger
        pub.subscribe(self.file_loaded, "file.loaded")
        self.students = students

    def file_loaded(self, status, file):
            self.CreateGrid(self.students.data.shape[0], self.students.data.shape[1])
            for i, col in enumerate(self.students.data.columns):
                self.SetColLabelValue(i, col)
            for i in range(self.students.data.shape[0]):
                for j in range(self.students.data.shape[1]):
                    self.SetCellValue(i, j, str(self.students.data.iloc[i, j]))
                    self.SetReadOnly(i, j)
            self.AutoSizeColumns()
        