import win32gui,win32con,time,win32api
import win32clipboard as Clp
class Wechat():
    def __init__(self):
        pass

    def _set_clipboard(self,text):
        Clp.OpenClipboard()
        Clp.EmptyClipboard()
        Clp.SetClipboardData(win32con.CF_UNICODETEXT,text)
        Clp.CloseClipboard()

    def _read_clipboard(self):
        Clp.OpenClipboard()
        res = Clp.GetClipboardData(win32con.CF_UNICODETEXT)
        Clp.CloseClipboard()
        return res



    def search(self,text):
        pass



