import win32com
from win32com.client import Dispatch,constants
class Word():
    def __init__(self,file_name):
        self.w = win32com.client.Dispatch('Word.Application')
        self.w.Visible = 1
        self.w.DisplayAlerts = 0
        self.doc = self.w.Documents.Open(file_name)

    def add_section(self,pre_index):
        pre_section = self.doc.Secitons(pre_index)
        new_section = self.doc.Range(pre_section.Range.End, pre_section.Range.End).Sections.Add()
        new_range = new_section.Range
        return new_range

    def add_words(self,w_range,content):
        w_range.InsertBefore(content)
    
    def add_para(self,section_range):
        content_pg = section_range.Paragraphs.Add()
        return content_pg.Range
    def set_para_color(self,para,color=255):#默认为是红色
        try:
            para + 1
            self.doc.Paragraphs(para).Range.Font.Color = color
        except TypeError:
            para.Range.Font.Color = color
#doc.Close()    
# content_pg.Range.Font.Name = 'Times New Roman'
# content_pg.Range.Font.Size = 24
# i = 0
# while True:
#     i+=1
#     try:
#         print(doc.Paragraphs(i).Range.Text)
#     except Exception:
#         break
    # def find_and_anchor(self,text):
    #     sel = self.w.Selection
    #     sel.TypeText(text)
    def change_content(self,OldStr,NewStr):
        self.w.Selection.Find.ClearFormatting()
        self.w.Selection.Find.Replacement.ClearFormatting()
        self.w.Selection.Find.Execute(OldStr, False, False, False, False, False, True, 1, True, NewStr, 2)

    def save(self,path=None):
        if path:
            self.doc.SaveAs(path)
        else:
            self.doc.Save()
    def close(self):
        self.w.quit()
if __name__ == '__main__':
    pass