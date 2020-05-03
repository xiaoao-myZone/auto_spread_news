from PIL import Image
import io
import os,re

class CompressImage():
    
    def __init__(self,img_path,byte_size=500):
        #byte_size单位为kb
        split_dir = os.path.split(img_path)
        self.main_path = split_dir[0]
        file_path = split_dir[1]
        res = re.search(r'([^\.]+)\.([^\.]+)',file_path)
        self.img_name = res.group(1)

        #target = r'\.([^\.]+?)$'#$表示从尾部匹配
        img_type = res.group(2)
        if not(img_type=='png' or img_type=='PNG'):
            self.path=os.path.join(self.main_path,self.img_name+'.png')
        else:
            self.path=img_path

        #输出图片的大小上限，单位为kb
        self.byte_size = byte_size
        self.img = Image.open(img_path)
        self.size = self.img.size
        self.img_byte = os.path.getsize(img_path)/1024

    def _get_byte_size(self,res):
        imgByteArr = io.BytesIO()
        res.save(imgByteArr, format='PNG')
        imgByteArr = imgByteArr.getvalue()

        return len(imgByteArr)

    def _estimate_for_rate(self,current_byte):
        "压缩倍率的1.5次方与图片大小成正比"
        raw_rate = pow(self.byte_size/current_byte,2/3)
        rate = round(raw_rate,2)#保留一位小数，四舍五入
        if not rate<raw_rate:#想要的直接去掉
            rate -= 0.01
        if rate<=0:
            print('##########缩放比例小于0#############\n')
            raise ValueError
        return rate

    def do_it(self):
        print('正在压缩图片...')
        rate = 1
        current_byte = 0
        for i in range(4):
            print('第%d次压缩....' %(i+1))
            if current_byte==0:
                current_byte = self.img_byte
            rate *= self._estimate_for_rate(current_byte)
            print('比率为{}'.format(round(rate,2)))

            #按比例缩小图片长宽
            new_size = (int(self.size[0]*rate),int(self.size[1]*rate))

            #压缩
            res = self.img.resize(new_size,Image.ANTIALIAS)

            #在虚拟内存中获取大小
            current_byte = self._get_byte_size(res)/1024
            print('大小为为{}kb\n'.format(round(current_byte,0)))
            
            if current_byte<self.byte_size:
                res.save(self.path,qulity=95)
                res.close()
                self.img.close()
                print('缩放倍率为%f' %rate)
                return self.path
            
        print('四次压缩都不能得到要求的大小，请自行截图处理图片。\n')

    def extendMargin(self,normal,suffix,margin_color='black',img_format='png'):
        delt_x = self.size[0]-normal[0]
        delt_y = self.size[1]-normal[1]
        width=0
        height = 0
        x=0
        y=0
        if delt_x<0:
            width = normal[0]
            x = -delt_x//2
        else:
            width = normal[0]+delt_x
        if delt_y<0:
            height = normal[1]
            y = -delt_y//2
        else:
            height = normal[1]+delt_y

        bg = Image.new("RGB",(width,height),margin_color)
        bg.paste(self.img,(x,y))
        out_path = os.path.join(self.main_path,self.img_name + '-' + suffix +'.' + img_format)
        bg.save(out_path)
        return out_path


if __name__=='__main__':
    # path = r'C:\Users\Administrator\Desktop\test\公众号\图片\1569198156.jpg'
    # C = CompressImage(path,500)
    # print(C.do_it())
    path = r'C:\Users\Administrator\Desktop\test\公众号\图片\157619507.png'
    C = CompressImage(path,500)
    #print(C.extendMargin((560,315),'autohome','white'))
    print(C.extendMargin((900,600),'pcauto','white'))

