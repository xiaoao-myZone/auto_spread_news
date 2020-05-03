import time
from datetime import datetime
#vip.126.com中的邮件列表中日期格式 2019年5月22日 16:38 (星期三)
class chi_fmt():

    def __init__(self):
        pass

    def contain_chi(self,word):
        for ch in word:
            if '\u4e00' <= ch <= '\u9fff':
                return True
        return False
    
    def from_chi_date(self,fmt):
        l_fmt = list(fmt)
        for i,char in enumerate(l_fmt):
            if char == '年':
                l_fmt[i] = '{y}'
            if char == '月':
                l_fmt[i] = '{m}'
            if char == '日':
                l_fmt[i] = '{d}'
        c_fmt = ''
        for char in l_fmt:
            c_fmt += char
        return c_fmt


class timetransfer():

    def __init__(self,time_format=None):
        if not time_format:
            self.fmt = '%Y-%m-%d %H:%M:%S'
        elif chi_fmt().contain_chi(time_format):
            self.fmt = chi_fmt().from_chi_date(time_format)
        else:
            self.fmt = time_format

    def s2f(self,time_stamp,fmt=None): 
        "transfer time stamp to formal time"
        "如果要用中文请用{y}的形式代替汉字'年'，同时(y='年',m='月',d='日',h='时',M='分',s='秒')"
        if not fmt:
            fmt = self.fmt
        if '{' in fmt:
            return datetime.fromtimestamp(time_stamp).strftime(fmt).format(y='年',m='月',d='日',h='时',M='分',s='秒')
        return datetime.fromtimestamp(time_stamp).strftime(fmt)
    
    def f2s(self,time_str,fmt=None):
        "tranfer formal time into time stamp"
        if not fmt:
            fmt = self.fmt
        if '{' in fmt:
            time_str = chi_fmt().from_chi_date(time_str)
        return datetime.timestamp(datetime.strptime(time_str,fmt))

if __name__ == '__main__':
    #fmt = '%Y年%m月%d日 %H:%M'
    fmt = ''
    kk = timetransfer(fmt)
    print(kk.s2f(1590000000))
    #print(kk.f2s('2019-05-22 23:17:42'))
    # 2019年5月22日 16:38
    # time_str = '2019年5月22日 16:38'

    # print(kk.f2s(time_str))

