#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
"""
来自：https://my.oschina.net/duxuefeng/blog/64137
"""
from win32com.client import Dispatch,constants
import win32com.client
from PIL import Image
from fractions import Fraction
import os

class EasyExcel: 
    """A utility to make it easier to get at Excel.  Remembering 
    to save the data is your problem, as is  error handling. 
    Operates on one workbook at a time.""" 
    def __init__(self, filename=None): 
        self.xlApp = win32com.client.Dispatch('Excel.Application') 
        if filename: 
            self.filename = filename 
            self.xlBook = self.xlApp.Workbooks.Open(filename) 
        else: 
            self.xlBook = self.xlApp.Workbooks.Add() 
            self.filename = '' 
    def _alert_image(self,image,scale=1,w_scale=1,h_scale=1,unit='dpi'):
        im = Image.open(image)
        n = None
        if unit == 'cm':
            rate = Fraction(254,7200)
            n = 2
        else:
            rate = 1

        if (w_scale>1 or h_scale>1) and (w_scale-1)*(h_scale-1)<=0:#只有一个设定值是绝对值
            if w_scale>1:                                          #宽是设定值
                scale = w_scale/im.size[0]
            else:                                                  #高是设定值
                scale = h_scale/im.size[1]
            return (round(im.size[0]*scale*float(rate),n),round(im.size[1]*scale*float(rate),n))
        else:       
            if w_scale>1:       #都是绝对设定值
                return (w_scale,h_scale)
            else:               #都不是绝对设定值
                return (round(im.size[0]*scale*w_scale*float(rate),n),round(im.size[1]*scale*h_scale*float(rate),n))

    def _delete_illegal_char(self,text):
        spt = os.path.split(text)
        main = spt[0]
        file = spt[1]
        "<  >  ?  [  ]  :  | 或 * "
        illegal_list=['<','>','?','[',']',':','|','*','/','\\']
        for i in illegal_list:
            file = file.replace(i,'')
        return os.path.join(main,file)

    def save(self, newfilename=None): 
        if newfilename:
            newfilename = self._delete_illegal_char(newfilename)
            while True:
                if os.path.exists(newfilename):
                    separated_name = newfilename.split('.')
                    newfilename = separated_name[0] + '-副本.' + separated_name[-1]
                else:
                    break                 
            self.xlBook.SaveAs(newfilename)#save()里面也可以带参数，作为文件名，保存同时修改文件名的意思吗？ 
        else: 
            self.xlBook.Save()    
    
    def close(self,change=False): 
        self.xlBook.Close(SaveChanges=change)#貌似无论是True还是False，结果都是不保存的##需要与Quit()联用？
        self.xlApp.Quit()
    
    def search(self,sheet,content):
        pass
    
    # def new_sheet(self,shtname):
    #     self.xlBook.add_sheet(shtname) 来自pyExcelerator
    def getCell(self, sheet, row, col): 
        "Get value of one cell" 
        sht = self.xlBook.Worksheets(sheet) 
        return sht.Cells(row, col).Value

    def setCell(self, sheet, row, col, value,color = None):#合并单元格会显示任意一个单元格的设置值
        "set value of one cell" 
        sht = self.xlBook.Worksheets(sheet) 
        sht.Cells(row, col).Value = value #用的是默认字体
        #sht.Cells (row, col).Interior.Color = color #指的是单元格背景颜色，搜索XlRgbColor
        
    def getRange(self, sheet, row1, col1, row2, col2): 
        "return a 2d array (i.e. tuple of tuples)" 
        sht = self.xlBook.Worksheets(sheet) 
        return sht.Range(sht.Cells(row1, col1), sht.Cells(row2, col2)).Value  #返回的是一个二维数组，两个Cells的四个参数，确定了表格区域的对角
        #range除了可以用数字表示外，还可以用excel自带的大写字母加数字表示，形如 Range('A1:A4')
   
    def rowNum(self,sheet):
        sht = self.xlBook.Worksheets(sheet)
        return sht.Range('A65536').End(-4162).Row #xlUp=-4162
   
    def deleteRow(self,sht,cell=None):
        sht = self.xlBook.Worksheets(sht)
        if cell:
            return sht.Range(cell).Delete()
        else:
            pass
            
    def addPicture(self, sheet, pictureName, Left=0, Top=0, Width=1, Height=1): 
        "Insert a picture in sheet" 
        sht = self.xlBook.Worksheets(sheet)
        size = self._alert_image(pictureName,w_scale=Width,h_scale=Height)
        sht.Shapes.AddPicture(pictureName, 1, 1, Left, Top, size[0], size[1]) 
        #left与Top表示图片距离左边框与上边框距离，width和height表示图片宽长，单位是磅，Excel中的行列宽单位也是磅
                                       
    def cpSheet(self, before=1): 
        "copy sheet" 
        shts = self.xlBook.Worksheets 
        shts(before).Copy(None,shts(before))#拷贝第一个sheet，并插在第一sheet后面 

if __name__ == '__main__':
    # file = r'C:\Users\Administrator\Desktop\碳材料实验室药品清单.xlsx'
    # image = r'C:\Users\Administrator\Desktop\python要求.png'
    # #ddir = r'C:\Users\Administrator\Desktop\信件打包\text.xlsx'
    # a = easyExcel(file)
    
    # #a.save(ddir)
    # a.addPicture('海藻酸钠',image,20,20,500)
    # a.close(True)
    path = r'C:\Users\Administrator\Desktop\test\qq.xlsx'
    sheet = 'Sheet1'
    companyname = '天风证券'
    companymail = '1006107210@qq.com'
    reversedate = '2019/6'
    Excel = EasyExcel(path)
    Excel.setCell(sheet,5,3,companyname)
    Excel.setCell(sheet,5,5,companymail)
    Excel.setCell(sheet,6,5,reversedate)
    Excel.save(r'C:\Users\Administrator\Desktop\test\ww.xlsx')
    Excel.close()
    #print(constants.rgbWhite)


    
    # print(a._alert_image(image,w_scale=500))