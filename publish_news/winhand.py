import win32gui,win32con,time,winsound,win32api
class Winhand():
    def __init__(self):
        pass
    
    def _wait_for_upload_window(self,wait_time=4):
        for i in range(4):
            time.sleep(1)
            dialog = win32gui.FindWindow('#32770','打开')
            if dialog:
                return dialog
        int(i)
        return 0
    def _send_path(self,edit_win,file_path):
        res = win32gui.SendMessage(edit_win, win32con.WM_SETTEXT, None,file_path)
        for i in range(3):
            if res!=1:
                print('传入参数失败')
                time.sleep(1)
                res = win32gui.SendMessage(edit_win, win32con.WM_SETTEXT, None,file_path)
            else:
                break
        int(i)
        

    def upload_file(self,file_path):
        time.sleep(1)
        dialog = self._wait_for_upload_window()
        time.sleep(0.3)
        if not dialog:
            print('获取文件上传窗口失败。\n')
            return False
        ComboBoxEx32 = win32gui.FindWindowEx(dialog, 0, 'ComboBoxEx32', None)
        ComboBox = win32gui.FindWindowEx(ComboBoxEx32, 0, 'ComboBox', None)
        Edit = win32gui.FindWindowEx(ComboBox, 0, 'Edit', None)
        button = win32gui.FindWindowEx(dialog, 0, 'Button', None)
        self._send_path(Edit,file_path)
        #win32gui.SendMessage(Edit, win32con.WM_SETTEXT, None,file_path)
        win32gui.SendMessage(dialog, win32con.WM_COMMAND, 1, button)
        return True

    def sonic_warn(self,fre=450,dur=600):
        winsound.Beep(fre,dur)

    def scroll_mouse(step=-1):
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL,0,0,step)

