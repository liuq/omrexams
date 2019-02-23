import wx.grid as gridlib
from pubsub import pub

class StudentsGrid(gridlib.Grid):
    def __init__(self, students, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pub.subscribe(self.file_loaded, "file.loaded")
        self.students = students

    def file_loaded(self, status, file):
            self.CreateGrid(self.students.students.shape[0], self.students.students.shape[1])
            for i, col in enumerate(self.students.students.columns):
                self.SetColLabelValue(i, col)
            for i in range(self.students.students.shape[0]):
                for j in range(self.students.students.shape[1]):
                    self.SetCellValue(i, j, str(self.students.students.iloc[i, j]))