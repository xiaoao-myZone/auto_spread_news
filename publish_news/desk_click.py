import pyautogui as p

class Desk_Click():
    def __init__(self):
        self.nav_box = (0,1030,1920,1080)

    def search_img(self,img_path,region=None,grayscale=False):
        "返回一个Box类对象，如Box(left=1416, top=562, width=50, height=41)"
        if not region:
            return p.locateOnScreen(img_path,grayscale=grayscale)
        elif region=='bottom':
            return p.locateOnScreen(img_path,region=self.nav_box,grayscale=True)
        else:
            return p.locateOnScreen(img_path,region=region,grayscale=grayscale)

    def click(self,target):
        length = len(target)
        if length==2:
            p.click(target[0],target[1],button='left')
        elif length==4:
            point = p.center(target)
            p.click(point[0],point[1],button='left')
if __name__=='__main__':
    wechat_path = r'C:\Users\Administrator\Desktop\test\images\imgs\wechatcoin_1.png'
    D = Desk_Click()
    D.click(D.search_img(wechat_path,region='bottom',grayscale=True))
