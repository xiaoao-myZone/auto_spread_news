from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException,TimeoutException,\
    ElementClickInterceptedException,StaleElementReferenceException,ElementNotInteractableException,\
    UnexpectedAlertPresentException
from selenium.webdriver.common.action_chains import ActionChains
import json,time,os,re,copy,traceback
import requests,bs4
from timetransfer import timetransfer
from winhand import Winhand
from wechat import Wechat
from functools import wraps
from cropimg import tailer
from compress_img import CompressImage

"""
关于cookie
    1.get_cookies()的方法可以收集到很多cookie，但是只有一些是真正有用的

    2.cookie需要与载入该网站时，与网站在本地建立的一些信息相结合才能发挥作用，也就是说，加载cookie后，首次访问可能还是无法登陆
       
       比如163，并且需要先载入再加载，并且需要切换到该窗口
    3.toutiao载入cookie后还需要点击登陆按钮，光是刷新是不行的

    4.有个页面的发布页面按下ctrl+a时容易全选

    5.可能遇到的限制: ①图片数量不够三图 ②第一张图片大小达不到要求(长宽分别大于560*315) ③标题字数11-30（网易:11,车友：30，它们的计数方式不太一样）

    6.正文格式：sina对几乎抹去除换行以外的一切格式，baidu，maiche对dayu的加粗不敏感，dayu对163的加粗不敏感
               一点号，大风号，头条号，微博，有车号对大鱼格式都敏感，趣头条，车家号对dayu的格式都不敏感，
               weixin对dayu加粗敏感
    7.selenium运用的坐标系的单位长度是电脑屏幕坐标系单位长度的0.8倍，chrome全屏状态下页面据桌面上端186个长度

    8.不接受二维码的平台：搜狐、百度、大风、趣头条

    9.登陆存在问题的平台:有车号（需要登陆主页然后依次点进链接），趣头条（需要点击首页的登陆）

    10.自动选封面可能遇到选择不全的问题，（大鱼，百度）

    11.将微信文章直接复制到大鱼，然后在复制粘贴，平台车家号，百度号，趣头条载入不了图片

    12.敏感词={'大风号': '毛泽东','朱镕基';'车家号': '毛泽东'}

    13.腾讯文档在周末会出现文章无法上传的情况


"""


###路径设置####
current_path = os.path.abspath(__file__)
current_path = os.path.split(current_path)[0]
current_path = os.path.split(current_path)[0]
current_path = os.path.join(current_path,'公众号')
img_path = os.path.join(current_path,'图片')
#img_path=r'C:\Users\Administrator\Desktop\test\公众号\报告\img'
#搜狐汽车品牌对应表文件
#branch_path = os.path.join(current_path,'报告','info','branch.json')

class Web():

    def __init__(self,driver,source,message,use='',code='',current_path='',add_intro=False):
        #具体用于从一个页面的url判断该平台是否成功发表文章，并转到相应网页
        self.published_signal = '该文字仅作为一种非空填充'

        self.driver = driver

        #平台的中文名，方便在某段进程中进行提醒
        self.source = source

        self.current_path = current_path
        self.img_path = os.path.join(self.current_path,'图片')
        self.shot_img_path = os.path.join(self.current_path,'报告','img')
        #接受从原搞分析得到的信息，比如标题，导语，封面路径等
        self.message = message

        #用户与密码
        self.use = use
        self.code = code

        #定位到标题和导语元素的引索方式
        self.title_locator=()
        self.intro_locator=()
        if add_intro:
            try:
                self.intro = message['introduce']
            except (KeyError,TypeError):
                self.intro = None
        else:
            self.intro = None

        #默认为True，在具体平台操作中会先检查导语是否还存在，在将其设置为相应的bool值
        self.introduce_exist=True#防止手动拷贝正文时已去掉导语，在modify_content中误删第一段(图)

        #其他属性
        self.locator = ''#如果有frame需要填写这个属性
        self.body = ()
        self.conbine = True#黏贴正文的定位是否需要添加self.paras_tag
        self.paras_tag='p'
        self.bold='strong'
        self.heading = 'h1'

        self.imgs_tag = ''#正文中图片的标签,img或者figure(微博，子标签还是img)
        self.imgs_id = ''#正文中图片的id
        
        self.cover_xpath = ''

        self.published_signal=''
        #是否添加导语到正文中


        #收集链接
        self.content_list_path = ''
        self.title_url_path = ''#并列的文章子标签下面的包含标题与链接的路径
        #如果复杂可以改写self._status
        self._state_path = ''#并列的文章子标签下面的包含发布状态的路径
        self.published_state = '已发布'

        self.read_count_path = ''#并列的文章子标签下面的包含阅读量的路径

        self.next_page_path = ''#翻到下一页的查找按钮路径

        self.search_path = ''#文章搜索框路径

        self.search_button_path = ''#文章搜索确认按钮路径
        


    ##tools
    def find(self,locator,method=By.XPATH):
        return self.driver.find_element(method,locator)
    
    def finds(self,locator,method=By.XPATH):
        return self.driver.find_elements(method,locator)

    def find_with_no_error(self,locator,method=By.XPATH):
        try:
            return self.driver.find_element(method,locator)
        except NoSuchElementException:
            return False

    def _change_html(self,element,content):
        js = 'arguments[0].innerHTML=arguments[1]'
        self.driver.execute_script(js,element,content)

    def _js_click(self,element):
        time.sleep(0.3)
        self.driver.execute_script("arguments[0].click()",element)

    def focus_on(self,element):
        js = 'arguments[0].focus();'
        self.driver.execute_script(js,element)

    def _wait_for(self,time,locator):
        return WebDriverWait(self.driver,time,0.2).until(EC.presence_of_element_located(locator))

    def _wait_for_displayed(self,time,locator):
        return WebDriverWait(self.driver,time,0.2).until(EC.visibility_of_element_located(locator))

    def _wait_for_all_displayed(self,time,locator):
        return WebDriverWait(self.driver,time,0.2).until(EC.visibility_of_all_elements_located(locator))

    def _wait_for_clickable(self,time,locator):
        return WebDriverWait(self.driver,time,0.2).until(EC.element_to_be_clickable(locator))

    def _wait_for_all(self,time,locator):
        return WebDriverWait(self.driver,time,0.2).until(EC.presence_of_all_elements_located(locator))
    
    def _wait_for_invisible(self,time,locator):
        WebDriverWait(self.driver,time,0.2).until(EC.invisibility_of_element_located(locator))
    
    def _wait_for_element_invisible(self,time,element):
        WebDriverWait(self.driver,time,0.2).until(EC.invisibility_of_element(element))

    def scroll_to_bottom(self):
        js="var q=document.documentElement.scrollTop=100000"
        self.driver.execute_script(js)

    def scroll_to_top(self):
        js="var q=document.documentElement.scrollTop=0"
        self.driver.execute_script(js)
    
    def scroll_to(self,y):
        "按照绝对坐标移动，以窗口顶部到达目标值为止，不过这要求y的值小于网页长度减去界面高度的值"
        js="var q=document.documentElement.scrollTop={}".format(y)
        self.driver.execute_script(js)

            
    def get_new_handle(self,current_handles=None):
        if current_handles==None:
            return self.driver.window_handles[-1]
        else:
            new_handles = self.driver.window_handles
            res = list(set(new_handles) - set(current_handles))[0]
            return res

    def get_into_frame(self):
        frame = self._wait_for(2,(By.XPATH,'.//iframe'))
        self.driver.switch_to.frame(frame)


    ##main_block
    def login(self,use,code):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        print('%s请自行登录\n' %self.source)
        print('%s的帐号:%s\n\t密码:%s' %(self.source,self.use,self.code))
    
    def is_logged(self):
        self.driver.implicitly_wait(3)
        try:
            self._wait_for(2,(By.XPATH,'//*[contains(text(),"帮宁工作室")]'))
        except TimeoutException:
            print('%s首次登录没有成功。\n' %self.source)
            return False
        return True
    
    def paste(self,part):
        if part == 'title':
            self._paste_title()

        elif part == 'body':
            self.scroll_to_top()
            if self.locator:
                self.switch_to_frame(locator=self.locator)
            if self.conbine:
                body_locator = (By.XPATH,self.body+'/'+self.paras_tag)
            else:
                body_locator = (By.XPATH,self.body)
            self.ctrl_v(body_locator,self.intro)
            if self.locator:
                self.driver.switch_to.parent_frame()
        else:
            print('请输入"title"或者"body"。\n')

    def modify_content(self,exe=False):
        pass

    def check_box(self,again=True):
        pass

    def check_published(self,url):
        if self.published_signal in url:
            return True
        else:
            return False

    def _status(self,element):#默认不做文字提取，但一般是要的
        data = element.find_element_by_xpath(self._state_path).text
        return data

    def _get_read_counts(self,element):#将阅读量字符串转换成数字
        data = element.find_element_by_xpath(self.read_count_path).text

        return self._strip_read_counts(data)
    
    def _strip_read_counts(self,data):#适合以逗号分割不省略尾部数字的情况
        if data==-1:
            return -1
        counts = re.search(r'(\d+)(,)?(\d+)?',data).group()
        parts = counts.split(',')
        dst = ''
        for i in parts:
            dst+=i

        return int(dst)

    def collect_info(self,title,next_page=False,read_count=False):#暂时只适合需要翻页的内容管理
        essay_list = self._wait_for_all(4,(By.XPATH,self.content_list_path))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath(self.title_url_path)
            full_title = title_and_url.text
            #print(full_title)
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != self.published_state:
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                
                res['read_counts'] = self._get_read_counts(i)

                # if read_count:
                #     res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res

        else:
            if next_page and essay_list:

                sbox = self._wait_for_clickable(3,(By.XPATH,self.search_path))
                self.text_box(sbox,title)
                button = self.find(self.search_button_path)
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=False,read_count=read_count)
                
                else:
                    return {}

                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

    ##editor
    def refresh(self,times=4):
        self.driver.set_page_load_timeout(10)
        count = 0
        while True:
            if count<times:
                count+=1
            else:
                print('第%d次刷新失败\n' %count)
                return

            try:
                if count>1:
                    print('正在执行第%d次刷新\n' %count) 
                self.driver.refresh()
                return 
            except TimeoutException:
                continue
   
    def _load_cover(self,element,again,img_path=None,js_click=True):#上传图片
        if img_path==None:
            img_path = self.message['cover_path']
        if element.tag_name == 'input':

            element.send_keys(img_path)
        
        else:
            if js_click:
                self._js_click(element)
            else:
                element.click()
            res = Winhand().upload_file(img_path)
            if not res:
                print('信息来源：%s' %self.source)
                if again:
                    time.sleep(1)
                    self._load_cover(element,again=False,img_path=img_path,js_click=js_click)
                else:
                    print('第二次上传图片失败。\n')

    def open_new_window(self,url,current_handles=None,quick_model=False):#在非快速模式下，打开新窗口并转入，并返回此窗口的handle
        "将打开链接前的句柄集与打开后的进行差集运算，得到新打开的窗口"
        if quick_model:
            js = 'window.open("%s")' %url
            current_handles = self.driver.window_handles
            self.driver.execute_script(js)
            self.get_new_handle(current_handles)

        else:
            js = 'window.open("")'
            self.driver.execute_script(js)#
            new_handle = self.get_new_handle(current_handles)
            self.driver.switch_to.window(new_handle)
            self.driver.get(url)#只有当driver.get(url)得到服务器响应了，该新建窗口的id才会被加入windows_handles中
            return new_handle
    
    def compulsive_click(self,web_element):
        for i in range(10):
            try:
                try:
                    ActionChains(self.driver).move_to_element_with_offset(\
                        web_element,5,5).click(web_element).perform()
                    break
                except Exception:
                    web_element.click()
                    break
            except Exception:
                time.sleep(0.2)
            int(i)
    
    def _get_text_from_html(self,html):
        "防止还有嵌套的子元素，不过暂时没必要"
        try:
            res = re.search(r'>(?P<text>[^<]*?)(</)',html).group('text')
        except (AttributeError,TypeError):
            return None
        return res

    def _strip_tags_in_text(self,text):
        if text:
            text = re.sub(r'<[^>]*?>','',text)
        return text

    def _check_element_is_empty(self,element):
        html_part = self._get_tag_html(element)
        print(html_part)
        text = self._get_text_from_html(html_part)
        print(text)
        text = self._strip_tags_in_text(text)
        print(text)
        if text:
            return False
        else:
            return True

    def ctrl_v(self,body_locator,introduce=None):#点击-清空-复制，清空可能会造成body失效，比如对163网站而言
        try:
            body = self._wait_for_clickable(6,body_locator)
        except TimeoutException:#把文章从车友号复制到车家号时，发现page_source只有html,head,body这三个标签
            self.driver.switch_to.parent_frame()
            body = self._wait_for_clickable(6,body_locator)
        self.compulsive_click(body)
        body = self._wait_for_clickable(10,body_locator)#点击以后body会发生变化，导致StaleElement错误
        #self.focus_on(body)
        time.sleep(0.5)
        if introduce == None:
            if not introduce:
                introduce = ' '#确保introduce第一行不能是空的，以免点击到文首的图片
            if body.text:
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)\
                    .key_down(Keys.BACKSPACE).key_up(Keys.BACKSPACE).pause(1).key_down(\
                        Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            else:
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        else:
            try:
                text = body.text
            except StaleElementReferenceException:#主要是搜狐出现了多次这样的错误，通过重新对body进行等待解决
                pass

            if text:
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)\
                .key_down(Keys.BACKSPACE).key_up(Keys.BACKSPACE).pause(1).send_keys(\
                    introduce).key_down(Keys.ENTER).key_up(Keys.ENTER).key_down(\
                        Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            else:
                ActionChains(self.driver).send_keys(introduce).key_down(Keys.ENTER).key_up(\
                    Keys.ENTER).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()

    def ctrl_c(self,body_locator):#全选复制
        try:
            body = self._wait_for_clickable(6,body_locator)

        except TimeoutException:
            body = self._wait_for(1,body_locator)
        #body.location_once_scrolled_into_view
        self.compulsive_click(body)
        
        #self.focus_on(body)
        time.sleep(0.5)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).\
            key_down(Keys.CONTROL).send_keys('c').key_up(Keys.CONTROL).perform()

    def delete_info(self,web_element):
        try:
            web_element.send_keys(Keys.CONTROL,'a')
        except ElementNotInteractableException:
            time.sleep(2)
            web_element.send_keys(Keys.CONTROL,'a')
        web_element.send_keys(Keys.DELETE)

        if web_element.text:
            print('##%s的标题没有清理干净\n')

    def _wait_for_copy(self):
        "从图片是否载入完成来判断是否可以复制"
        imgs_xpath = self.body + '//' + self.imgs_tag + '[contains(@src,"%s")]' %self.imgs_id
        try:
            self._wait_for_all(10,(By.XPATH,'%s' %imgs_xpath))
            return True
        except TimeoutException:
            print('%s图片载入失败\n' %self.source)
            return False

    def copy(self):#专门为第一个平台做的
        if not self._wait_for_copy():
            Winhand().sonic_warn()
            ans = input('请手动重新载入后回车继续，按任意键退出')
            if ans:
                raise Exception

        self.modify_content(exe=True)
        time.sleep(1.5)

        self.scroll_to_top()
        time.sleep(3)
        anchor = (By.XPATH,self.body + '//' + self.paras_tag)
        self.ctrl_c(anchor)

    def paste_for_element(self,web_element):
        web_element.send_keys(Keys.CONTROL,'v')
    
    def _write_clipboard(self,txt):
        clipboard = Wechat()
        clipboard._set_clipboard(txt)

    def text_box(self,element,txt,clear=True):#向文本框输入内容
        self._write_clipboard(txt)
        self.delete_info(element)
        self.paste_for_element(element)
        if clear:
            self._write_clipboard('')

    def _paste_title(self):
        self._write_clipboard(self.message['title'])
        title = self._wait_for(10,self.title_locator)
        self.delete_info(title)
        self.paste_for_element(title)

    def _paste_intro(self):
        self._write_clipboard(self.message['introduce'])
        intro= self._wait_for(8,self.intro_locator)
        self.delete_info(intro)
        self.paste_for_element(intro)

    def _search_new_window(self,keyword=None):#转到并返回新窗口句柄
        handles = self.driver.window_handles
        if keyword:
            handles.reverse()
            for i in handles:
                self.driver.switch_to.window(i)
                print(self.driver.title)
                if keyword in self.driver.title:
                    return i
            else:
                print('没有找到对应的窗口。\n')
                return False
        else:
            res = handles[-1]
            self.driver.switch_to.window(res)
            return res
    
    def search_new_window(self,keyword=None,element=None,times=4):#可靠搜索
        "参数keyword与element不可以同时为None，输入需要点击的元素对象，返回句柄对象，不切换"
        if keyword:
            for i in range(times):
                res = self._search_new_window(keyword)
                if res:
                    return res
                else:
                    time.sleep(1)
            int(i)
        else:#问题在于，当一个页面在载入时，可以成功过返回它的handle吗？测试了一下，答案是‘是’
            pre_handles = self.driver.window_handles

            self._js_click(element)
            
            cur_handles = self.driver.window_handles
            res = list(set(cur_handles) - set(pre_handles))[0]
            return res
    

    def _paste(self,part,title_path,body_path,method=By.XPATH,text=None):
        if part == 'title':
            title = self._wait_for(4,(method,title_path))
            self.delete_info(title)
            title.send_keys(text)
            time.sleep(0.4)
        elif part == 'body':
            body_locator = (method,body_path)
            self.ctrl_v(body_locator)
        else:
            print('请输入"title"或者"body"。\n')

    def switch_to_frame(self,locator=None):
        if locator:
            frame = self._wait_for(4,locator)
        else:
            frame = self._wait_for(4,(By.XPATH,'.//iframe'))
        self.driver.switch_to.frame(frame)
    
    def _qqlogin(self,qq_href,use,code,):
        print('请手动处理。')
        return True
        # if qq_href:
        #     self.open_new_window(qq_href)
        # # js_qq = 'window.open("%s")' % qq_href
        # # self.driver.execute_script(js_qq)
        # # windows = self.driver.window_handles
        # # self.driver.switch_to.window(windows[1])
        # frame = self._wait_for(5,(By.XPATH,'.//iframe'))
        # #frame = driver.find_element_by_css_selector("iframe[id='ptlogin_iframe']")
        # self.driver.switch_to.frame(frame)
        # self.driver.find_element_by_css_selector("a[id='switcher_plogin']").click()
        # login = self.driver.find_element_by_css_selector("input[id='login_button']")
        # account = self.driver.find_element_by_id("u")
        # #user.clear()
        # self.delete_info(account)
        # account.send_keys(user)
        # pwd = self.driver.find_element_by_css_selector("input[type='password']")
        # #pwd.clear()
        # pwd.send_keys(psw)
        # time.sleep(0.3)
        # login.click()
        # over = self._wait_for(4,(By.XPATH,'//div[contains(text(),"手机验证")]'))
        # time.sleep(0.5)
        # if 'block' in over.get_attribute('style'):
        #     print('%s需要手机验证。\n' %self.source)
        #     return False
        # return True

    def _insert(self,word,target):
        fragments = word.split(target)
        for i in range(len(fragments)//2):
            fragments[i*2] += '\\'
        return target.join(fragments)

    def escape_word(self,word):
        "将字符变量引用到正则表达式中，如果不进行转义，会出现错误。"
        re_escape = ('\\','^','_','$','|','@','[',']','{','}','(',')','?','+','*','.')
        for i in re_escape:
            if i in word:
                word = self._insert(word,i)
        return word   
    
    def _modify_warning(self,num,i):
        res = False
        if num != 1:
            if num==0:
                print('#####%s在转换字段：%s-的格式时失败。\n' %(self.source,i))
            else:
                print('#####%s在转换字段：%s-的格式时变换了不止一次。\n' %(self.source,i))
                res=True
        else:
            res=True
        
        return res
        
    def delete_html_space(self,html):
        target = '&nbsp;'
        html = re.subn(target,'',html)
        return html

    def delete_para(self,html,charactor,target_para):

        target = r'<%s[^>]*>(<(?P<taga>[^>\s]*)[^>]*>)?%s(\s)?(<br>)?(</(?P=taga)>)?(<(?P<tagb>[^>\s]*)[^>]*></(?P=tagb)>)?</%s>' %(charactor,self.escape_word(target_para),charactor)
        #target = r'<%s[^>]*>%s(\s)?(<br>)?</%s>' %(charactor,self.escape_word(target_para),charactor)
        repl = ''
        res = re.subn(target,repl,html,count=1)
        deal = self._modify_warning(res[1],target_para)
        html = res[0]
        return (html,deal)

    def delete_introduce(self,html,charactor):
        intro = self.message['introduce']
        res = self.delete_para(html,charactor,intro)
        if res[1]:
            self.introduce_exist=False
        html = res[0]
        return html
    
    def delete_empty_paras(self,html):
        target = r'<p class="empty" (.*?)></p>'
        repl=''
        res = re.sub(target,repl,html)
        return res

    def delete_blank_para(self,html,para_tag):#貌似文章发出去后，平台都会删去多余的空行
        pass

    def delete_extra_para(self,html):#通用

        for i in self.message['extras']:
            res = self.delete_para(html,self.paras_tag,i)
            html = res[0]
        return html
    
    def _hide_element(self,element):
        self.driver.execute_script ("arguments[0].style=arguments[1]",element,"display: none;")

    def _modify_content_html(self,html,charactor_b,charactor_h,bold,heading,content=None,delete_intro=False):
        "不能对分段标签中含有属性的平台使用"
        if content:
            message = content
        else:
            message = self.message
        if delete_intro:
            html = self.delete_introduce(html,charactor_b)

        for i in message['bold']:
            target = r'<%s>(<span>)?%s(\s)?(<br>)?(</span>)?</%s>' %(charactor_b,self.escape_word(i),charactor_b)
            repl = '<{0}><{1}>{2}</{1}></{0}>'.format(charactor_b,bold,i)
            res = re.subn(target,repl,html)
            self._modify_warning(res[1],i)
            html = res[0]

        for i in message['heading']:
            target = r'<%s>(<span>)?%s(\s)?(<br>)?(</span>)?</%s>' %(charactor_h,self.escape_word(i),charactor_h)
            repl = '<{0}><{1}>{2}</{1}></{0}>'.format(charactor_h,heading,i)
            res = re.subn(target,repl,html)
            self._modify_warning(res[1],i)
            html = res[0]
        
        return html
    
    def _bold_names(self,html):
        for name in self.message['names']:
            pattern = r'<%s>(%s)(:|：)([^<]+)</%s>' %(self.paras_tag,name,self.paras_tag)
            add_bold_tag = lambda matched:'<%s><%s>%s</%s>%s%s</%s>' \
                                %(self.paras_tag, self.bold, matched.group(1), self.bold, matched.group(2), matched.group(3), self.paras_tag)
            res = re.subn(pattern,add_bold_tag,html)
            print('在%s中加粗了%d次人名:%s\n' %(self.source, res[1], name))
            html = res[0]

        return html
        
    def _np_modify(self,text):
        "只要是空格与&nbsp;同时出现，就需要删掉空格，根据情况有两种方法"
        bp = '&nbsp;'
        if bp in text:  #先检查&nbsp;+空格的组合，换成单个的&nbsp;
            target = r'%s\s+' %self.escape_word(bp)
            repl = bp
            res = re.subn(target,repl,text)
            if res[1]:
                return res[0]
            else:   #如果不是第一种，检查第二种空格+&nbsp;的组合，换成单个的&nbsp;
                target = r'\s%s' %self.escape_word(bp)
                res = re.subn(target,repl,text)
                if res[1]:
                    return res[0]
                else:
                    return False

    def _modify_blankspace(self,txts):#来自头条和搜狐
        "删除空格+&nbsp;中的空格"
        for num,i in enumerate(txts):
            first = re.sub(r'\s&nbsp;','&nbsp;',i)
            second = re.sub(r'&nbsp;\s','&nbsp;',first)
            txts[num] = second
        return txts

    def _get_tag_html(self,element):
        js = 'return arguments[0].innerHTML'
        return self.driver.execute_script(js,element)
    
    def _get_text_from_html(self,html):
        "防止还有嵌套的子元素，不过暂时没必要"
        try:
            res = re.search(r'>?(?P<text>[^<]+)(</)?',html).group('text')
        except (AttributeError,TypeError):
            return None
        return res

    def screen_shot_for_element(self,element,bias=(0,0,0,0),y_scroll=0):
        "y_scroll用来将截图窗口上下调整，负值为向上滑"
        "这时整个截图坐标也会向上移动，一般相应地需要bias增大下坐标不小于y_scroll的负值，才能截取到目标"
        "bias的修改顺序为：左，上，右，下，坐标原点在左上角"
        "截图利用的是当下窗口的相对坐标"
        "driver.screenshot()方法对不在初次载入屏幕内的元素会出现死循环"
        ##命名
        path=self.shot_img_path
        img_name = self.source + '-' + str(int(time.time())) + '.png'
        terminal_path = os.path.join(path,img_name)
        size = element.rect

        ##将元素摆在屏幕中方便截图
        start = element.location_once_scrolled_into_view #返回元素左上角相对当前窗口界面的相对坐标，正常情况y<10
        if start['y']<10:
            if self.source=='weibo':#微博文章列表有一个跟随窗口滑动的栏，会挡住需要截图的地方的上缘
                top_correct = size['y']-110#严格来说需要考虑如果是列表第一个元素，貌似不影响
            else:
                top_correct = size['y']-10
            self.scroll_to(top_correct + y_scroll)

            top = 0
        
        else:#说明窗口已经滑到底端了，截图框向上滑动10
            top = start['y'] - 10

        ##略微向下截取多一点
        correct_index = 0.77

        ##确定裁剪的矩形区域，截图框略微向左滑动
        left = size['x']-3
        
        right = left + size['width']
        bottom = top + size['height']

        box = (left+bias[0], top+bias[1], int(right/correct_index)+bias[2], int(bottom/correct_index)+bias[3])

        ##裁剪并保存
        self.driver.save_screenshot(terminal_path)#对整个页面截图
        res = tailer(terminal_path,box)
        res.save(terminal_path)
        return terminal_path
 
    def page_switch_test(self,times=6,interval=0.8):#测试文章管理中局部页面跳转是否可执行
        for i in range(times):
            time.sleep(interval)
            try:
                self.find('.//div')
                return True
            except StaleElementReferenceException:
                pass
        int(i)
        print('%s文章管理页面无法顺利跳转\n' %self.source)
        return False

    def _reopen_publish_window(self,pb_url,handles):
        "将当前url与输入的url进行比对，如果不一致则转到"
        if self.driver.current_url != pb_url:
            self.driver.get(pb_url)



######################百家号##############################
class Bjh(Web):#基本完成，基本测试通过
    
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'strong'
        self.heading = 'h3'
        self.body = './/body'
        self.charactor_b = 'p'
        self.charactor_h = 'p'
        self.title_locator = (By.XPATH,'.//div[@class="input-box"]/*[@placeholder]')
        self.published_signal = 'clue'
    
    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        print('dealing with baijiahao....')
        WebDriverWait(self.driver,10,0.5).until(EC.presence_of_element_located(\
                        (By.CSS_SELECTOR,"a[class='index-btn index-btn-login main-login']"))).click()

        WebDriverWait(self.driver,10,0.5).until(EC.text_to_be_present_in_element(\
                        (By.CSS_SELECTOR,"p[title='用户名登录']"),'用户名登录'))

        self.driver.find_element_by_css_selector("div[class='tang-pass-footerBar'] > p[title='用户名登录']").click()
        ## 用户名跟密码的设置并点击提交
        user = self.driver.find_element_by_name('userName')
        #user.clear
        pwd = self.driver.find_element_by_name('password')
        #pwd.clear()
        submit = self.driver.find_element_by_id('TANGRAM__PSP_4__submit')
        user.send_keys(use)
        pwd.send_keys(code)
        submit.click()

    def paste(self,part):#直接粘贴
        if part == 'title':
            self._paste_title()
        elif part == 'body':
            self.switch_to_frame()
            #body_locator = (By.XPATH,'.//body/p')
            body_locator = (By.XPATH,'%s/p' %self.body)
            self.ctrl_v(body_locator,self.intro)
            self.driver.switch_to.parent_frame()
        else:
            print('请输入"title"或者"body"。\n')
    
    def modify_content(self):
        "全文0级结构，段落有编号，需要保存"
        "完美继承头条号字体"
        # self.switch_to_frame()
        # body = self.find('.//body')
        # html = self._get_tag_html(body)
        # for i in self.message['bold']:
        #     target = r'<p{1}(?P<id>[^>]*?)>%s(\s)?</p>' %self.escape_word(i)
        #     repl = r'<p\g<id>><%s>%s</%s></p>'  %(self.bold,i,self.bold)
        #     html = re.sub(target,repl,html)
        # for i in self.message['heading']:
        #     target = r'<p{1}(?P<id>[^>]*?)>%s(\s)?</p>' %self.escape_word(i)
        #     repl = r'<%s\g<id>>%s</%s>'  %(self.heading,i,self.heading)
        #     html = re.sub(target,repl,html)

        # self._change_html(body,html)
        # self.driver.switch_to.parent_frame()
    
    def test_decorator(self):
        print('It works.')
    
    def _select_button(self,e_path):
        time.sleep(0.5)
        buttons = self.driver.find_elements_by_xpath(e_path)#存在两个相同的button难以分开
        for i in buttons:
            if i.is_displayed():
                i.click()
                break
    
    def _click_it(self,e_path):
        for i in range(5):
            time.sleep(1)
            self.find(e_path).click()
            checked = self.find('%s/..' %e_path)
            if 'checked' in checked.get_attribute('class'):
                return True
        print('未能成功点击按钮。\n')
        int(i)
        return False

    def _select_single_cover(self,cover_num):
        self._wait_for_clickable(4,(By.XPATH,'.//div[@class="cover-list cover-list-one"]//div[@class="container"]')).click()#开始选择图片
        img_list = self._wait_for_all(2,(By.XPATH,'.//div[@class="ant-modal-content"]//div[@class="item "]'))
        img_list[cover_num-1].click()#选中图片
        buttons_path  = './/div[@class="ant-modal-content"]//span[text()="确 定"]/..'
        self._select_button(buttons_path)#选择可以点击的button
    
    def _auto_pick_img(self):
        check = self._wait_for(5,(By.XPATH,'.//*[contains(text(),"系统正")]'))
        while True:
            try:
                check.is_displayed()
                time.sleep(0.3)
            except StaleElementReferenceException:
                return True

    def check_box(self,cover_num=1):#不一定能自动生成三图，需要自行检查
        self.scroll_to_bottom()
        e_path_1 = './/span[text()="三图"]'
        e_path_2 = './/span[text()="单图"]'
        #三图
        if self.message['imgs_num']>2:
            path_1 = self.find(e_path_1)
            self._js_click(path_1)
            #self._auto_pick_img()
            #imgs = self._wait_for_all(2,(By.XPATH,'.//div[@class="cover-list cover-list-three"]//div[@class="DraggableTags-tag"]'))
            try:
                self._wait_for_displayed(4,(By.XPATH,'.//div[@class="cover-list cover-list-three"]//div[contains(@class,"BaseImage")]/div'))
            except TimeoutException:
                triple = self._wait_for(3,(By.XPATH,'.//div[@class="cover-list cover-list-three"]//div[@class="DraggableTags-tag"][1]//span'))
                self._js_click(triple)
                img_list = self._wait_for_all(5,(By.XPATH,'.//div[@class="ant-modal-content"]//div[@class="item "]'))
                for num in range(3):
                    self._js_click(img_list[num])
                buttons_path  = './/div[@class="ant-modal-content"]//span[text()="确 定"]/..'
                self._select_button(buttons_path)
        else:
            path_2 = self.find(e_path_2)
            self._js_click(path_2)#自动生成，并且和三图的第一张是同一个元素
            try:
                img = self._wait_for_displayed(4,(By.XPATH,'.//div[@class="cover-list cover-list-one"]//div[contains(@class,"BaseImage")]/div'))#等待载入
                ActionChains(self.driver).move_to_element_with_offset(img,90,60).perform()#移动到图片，触发图片上的删除按钮，图片的大小正好是180×120
                btn_1 = self._wait_for(5,(By.XPATH,'.//div[@class="cover-list cover-list-one"]//span[@class="op-remove "]'))#删除
                self._js_click(btn_1)
                self._select_single_cover(cover_num)
            except TimeoutException:
                self._select_single_cover(cover_num)


        #分类:
        self.scroll_to_bottom()
        classfication = self.find('.//label[@title="分类"]/../..')
        arrow = classfication.find_element_by_xpath('.//span[@class="ant-select-arrow"]')
        self._js_click(arrow)
        car = self._wait_for_displayed(2,(By.XPATH,'.//ul[@role="menu"]/li[text()="汽车"]'))
        self._js_click(car)
        
        #原创申明:
        self.scroll_to_bottom()
        if self.message['original']:
            org_claim = self.find('.//label[text()="声明原创"]/../..')
            button = org_claim.find_element_by_xpath('.//button')
            self._js_click(button)
            confirm = self._wait_for_displayed(3,(By.XPATH,'.//div[text()="声明原创"]/../..'))
            confirm = confirm.find_element_by_xpath('.//span[text()="确 定"]/..')
            self._js_click(confirm)
            self._wait_for(4,(By.XPATH,'.//label[text()="声明原创"]/../..//span[text()="已声明"]'))
        
        #设置(自荐)  有两个input，一个是自荐，一个是自动优化标题，原创才能自荐

            if self.message['source'] == 'weixin':
                setting = self.find('.//label[@title="设置"]/../..')
                times = setting.find_element_by_xpath('.//span[contains(text(),"自荐")]/span[@style]').text
                if times != '0':
                    try:
                        button = self._wait_for(2,(By.XPATH,'.//label[@title="设置"]/../..//span[@class="ant-checkbox"]'))
                        self._js_click(button)
                    except TimeoutException:
                        pass
                        
    def publish(self):
        button = self.find('.//span[@class="op-list"]/button/span[text()="发 布"]/..')
        self._js_click(button)

    def _status(self,element):
        return element.find_element_by_xpath('.//span[@class="article-status-desc"]').text
    
    def collect_info(self,title,next_page=False,start=0,read_count=False):#搜索两页
        essay_list = self._wait_for_all(4,(By.XPATH,'.//div[@class="client_pages_content"]/div[@class="article-list-wrap "]'))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath('.//a[@class="title-link"]')
            full_title = title_and_url.text
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                data = i.find_element_by_xpath('.//div[@class="article-data-wrap"]/span[2]').text
                res['read_counts'] = self._strip_read_counts(data)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res
        else:
            if next_page and essay_list:

                sbox = self._wait_for_clickable(3,(By.XPATH,'.//*[contains(@class,"search")]//input'))
                self.text_box(sbox,title)
                button = self.find('.//*[contains(@class,"search")]//button')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=False,read_count=read_count)
                
                else:
                    return {}


                # next_button = self.find('.//li[@title="下一页"]')#未测试
                # next_button.click()
                # return self.collect_info(title,next_page=False,start=start,read_count=read_count)
            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

######################微博##############################
class Weibo(Web):#搜索
    
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'b'
        self.heading = 'b'
        self.body = './/div[contains(@class,"WB_editor_iframe_new")]'  
        self.title_locator = (By.XPATH,'.//div[@class="title"]//textarea')
        self.intro_locator = (By.XPATH,'.//div[@class="preface"]/input')
        self.charactor = 'p'
        self.introduce_exist=True
        self.published_signal = 'history'

    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        print('dealing with weibo....')
        #微博首页加载时间太长，没必要用隐式等待
        login = WebDriverWait(self.driver,15,0.5).until(EC.presence_of_element_located(\
                        (By.XPATH,"//*[@id='pl_login_form']/div/div[3]/div[6]/a")))
        user = self.driver.find_element_by_id('loginname')
        user.clear()
        user.send_keys(use)
        pwd = self.driver.find_element_by_name('password')
        pwd.clear()
        pwd.send_keys(code)
        login.click()
        verification = self._wait_for(1,(By.XPATH,'//input[@value="验证码"]/../..'))
        if verification.get_attribute('style') == 'display: none;':
            return#登陆成功后首页网址特征字符
        else:
            print('%s需要输入验证码。\n' %self.source)
            #貌似在弹出验证码窗口时可以刷新一下就可以进入了

    def _paste_ready(self):
        url = self.driver.current_url
        start = url.rfind('/') + 1
        try:
            int(url[start:])
            return True
        except ValueError:
            return False
        
    def paste(self,part):
        new_handle = ''
        if not self._paste_ready():
            try:
                target = self._wait_for(4,(By.XPATH,'.//div[@class="func_area clearfix"]//a[@title="头条文章"]'))
                new_handle = self.search_new_window(element=target)
                self.driver.close()
                self.driver.switch_to.window(new_handle)
            except TimeoutException:
                pass

        #标题
        if part == 'title':
            try:
                add_new = self._wait_for_clickable(2,(By.XPATH,'.//a[text()="创作一篇新文章"]'))
                add_new.click()
            except TimeoutException:
                pass
            self._paste_title()
            # title_input = self._wait_for_clickable(8,(By.XPATH,'.//div[@class="title"]//textarea'))
            # self.delete_info(title_input)
            # title_input.send_keys(self.message['title'])
            self._paste_intro()
            # introduce_input = self._wait_for_clickable(4,(By.XPATH,'.//div[@class="preface"]/input'))
            # self.delete_info(introduce_input)
            # introduce_input.send_keys(self.message['introduce'])
            if new_handle:
                return new_handle
        elif part == 'body':
            head = self.find('%s/*' %self.body)
            if head.tag_name=='figure':
                #first_para = self.find('.//div[contains(@class,"WB_editor_iframe_new")]/p')
                first_para = self.find('%s/p' %self.body)
                first_para.location_once_scrolled_into_view
            #body_locator = (By.XPATH,'.//div[contains(@class,"WB_editor_iframe_new")]/p')
            body_locator = (By.XPATH,'%s/p' %self.body)
            self.ctrl_v(body_locator,self.intro)

        else:
            print('请输入"title"或者"body"。\n')

    def modify_content(self):
        body = self.find(self.body)
        html = self._get_tag_html(body)
        html = self.delete_introduce(html,'p')
        #往往把第一段删除了
        # if self.introduce_exist:
        #     html = self.delete_fisrt_para(html)
        # self._change_html(body,html)
        self._change_html(body,html)

    def delete_fisrt_para(self,html):
        i = 1
        while True:
            first_para = self.find('.//div[contains(@class,"WB_editor_iframe_new")]//p[%d]' %i)
            if first_para.text:
                sp_introduce_html = self._get_tag_html(first_para)
                sp_introduce = self._get_text_from_html(sp_introduce_html)
                print('第二次删除的导语为:%s\n' %sp_introduce)
                res = self.delete_para(html,self.charactor,sp_introduce)
                if res[1]:
                    print('%s的导语第二次删除成功。' %self.source)
                else:
                    print('#####%s的导语第二次删除没有成功' %self.source)
                return res[0]
            else:
                i+=1

    def check_box(self,cover_num=1):
        self.scroll_to_bottom()
        set_cover = self.driver.find_element_by_xpath('//div[text()="设置封面"]/..//div[@class="upload"]/div')
        self._js_click(set_cover)
        self._wait_for(5,(By.XPATH,'//div[@class="W_layer "]//a[text()="上传"]/input'))\
            .send_keys(self.message['cover_path'])
        self._wait_for(5,(By.XPATH,'.//div[@class="list_wrap"]//ul/li[contains(@class,"info")]'))
        self._wait_for_invisible(12,(By.XPATH,'.//div[@class="list_wrap"]//ul/li[contains(@class,"info")]'))
        time.sleep(2.5)#如不等待，封面容易变成前一个，而不是目前在上传的。
        button = self._wait_for(5,(By.XPATH,'//div[@class="pic_list"]//ul/li[1 and @class="picbox"]/div'))
        self._js_click(button)
                            #当上传完成时，第一个li的class由picbox_info变成picbox
        time.sleep(0.4)
        self.find('//div[@class="W_layer "]//div/a[text()="确定"]').click()
        self._wait_for(5,(By.XPATH,'.//div[@class="content"]//div[@class="cropper-wrap-box"]//img'))
        self.find('//div[@class="W_layer "]//div/a[text()="确定"]').click()
        #self.driver.find_element_by_xpath('//span[@class="next"]/a').click()

    def publish(self):#
        next_step = self.find('.//span[@class="next"]/a[text()="下一步"]')
        self._js_click(next_step)
        publish = self._wait_for(4,(By.XPATH,'.//div[@class="content"]//div[@class="func"]/a'))
        self._js_click(publish)

    def collect_info(self,title,read_count=False,next_page=False):
        current_handle = self.driver.current_window_handle
        essay_list = self._wait_for_all(10,(By.XPATH,'.//div[@node-type="feed_list"]/div[@tbinfo="ouid=5646432272"]'))
        res = dict()
        for i in essay_list:
            try:
                source_element = i.find_element_by_xpath('.//a[@action-type="app_source"]')
                target = i.find_element_by_xpath('.//a[@action-type="feed_list_url"]')
                complete_title_ele = i.find_element_by_xpath('.//div[@node-type="feed_list_content"]')
                raw_text = complete_title_ele.text
                if '新浪看点' in raw_text:
                    continue
                match = re.search(r'《(.*?)》',raw_text)
                if match:
                    full_title = match.group(1)
                else:
                    print('%s搜索出现错误。\n' %self.source)
                    return {}
                #full_title  = target.get_attribute('title')#对较长的标题，尾部字符会以省略号代替
            except NoSuchElementException:#一些其他动态或者不完整的文章会报错
                continue
            if '微博' in source_element.text and title in full_title:
                read_text = i.find_element_by_xpath('.//i[contains(@title,"此条微博已经被阅读")]').text
                read_counts = self._strip_read_counts(read_text)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)
                    
                href = target.get_attribute('href')
                self.open_new_window(href)
                res['title'] = full_title
                res['url'] = self.driver.current_url
                res['read_counts'] = read_counts
                self.driver.close()


                self.driver.switch_to.window(current_handle)
                return res
        else:
            if read_count:
                
                sbox = self._wait_for_clickable(3,(By.XPATH,'.//*[contains(@class,"search")]//input[contains(@notice,"我的")]'))
                self.text_box(sbox,title)
                button = sbox.find_element_by_xpath('./..//a[@title="搜索"]')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=False,read_count=read_count)
                
                else:
                    return {}


            print('没有在%s中搜到所要的文章。\n' %self.source)
            self.driver.switch_to.window(current_handle)
            return {}

######################新浪##############################
class Sina(Web):#搜索  继承头条号的加粗，不继承小标题
    
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'strong'
        self.heading = 'strong'
        self.body = './/body'
        self.title_locator = (By.XPATH,'.//textarea[@placeholder="请输入标题"]')
        self.published_signal = 'ContentList'
        self.query_url = 'http://mp.sina.com.cn/#/ContentList/0'

    def is_logged(self):
        if self.message['model'] == 'pulish':
            try:
                self._wait_for(5,(By.XPATH,'.//aside[contains(@class,"edit")]'))
            except TimeoutException:
                return False
        else:
            try:
                self._wait_for(5,(By.XPATH,'.//span[contains(text(),"帮宁工作室")]'))
            except TimeoutException:
                return False
        return True             

        # "反选，看有没有登陆界面"
        # self.driver.implicitly_wait(3)
        # try:
        #     self._wait_for(1.5,(By.XPATH,'.//div[contains(@class,"btn") and text()="登录"]'))
        # except TimeoutException:
        #     return True
        # print('%s首次登录没有成功。\n' %self.source)
        # return False

    def _close_fuck_star(self):
        try:
            self.driver.find_element(By.XPATH,'//h1[text()="星级最新评定结果"]/../a').click()#关闭弹窗
        except Exception:
            pass

    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        print('dealing with sina....')
        try:
            login = WebDriverWait(self.driver,2,0.5).until(EC.presence_of_element_located(\
                        (By.CSS_SELECTOR,"button[class='btn1']")))
            login.click()
        except TimeoutException:
            pass
        login = WebDriverWait(self.driver,2,0.5).until(EC.presence_of_element_located(\
                        (By.CSS_SELECTOR,"a[class='login_btn']")))
        user = self.driver.find_element_by_css_selector("input[type='text']")
        user.send_keys(use)
        pwd = self.driver.find_element_by_css_selector("input[type='password']")
        pwd.send_keys(code)
        login.click()
        #检验是否需要验证
        again = True
        while True:
            try:
                WebDriverWait(self.driver,1,0.5).until(EC.presence_of_element_located(\
                            (By.CSS_SELECTOR,"input[class='login_ipt sp']")))
                if again:
                    print('Please input check code.')
                    again = False
            except TimeoutException:
                break
        #进入有弹窗
        self.driver.implicitly_wait(2)
        try:
            self.driver.find_element(By.XPATH,'//h1[text()="星级最新评定结果"]/../a').click()#关闭弹窗
        except Exception:
            pass
        return self.driver.current_url
        # if self.driver.current_url=publish:
        #     self.refresh_cookie('sina')
        #     return None

    def paste(self,part):
        if part == 'title':
            self._paste_title()
            # title = self._wait_for(4,(By.XPATH,'.//textarea[@placeholder="请输入标题"]'))
            # self.delete_info(title)#不知道textarea可不可以接受send_keys的操作
            # title.send_keys(self.message['title'])
        elif part == 'body':
            self.switch_to_frame()
            #body_locator = (By.XPATH,'.//body/p')
            body_locator = (By.XPATH,'%s/p' %self.body)
            self.ctrl_v(body_locator,self.intro)
        else:
            print('请输入"title"或者"body"。\n')
    
    def modify_content(self):
        "全文是0级结构，可设置的格式只有加粗，从车家号copy过来的段落含有style，但没有属性"
        "点击加粗后，是在p与里层标签之间加一个strong"
        "带格式的段落没有标签"
        self.switch_to_frame()
        body = self.find('.//body')
        html = self._get_tag_html(body)
        bold_content = self.message['bold']+self.message['strong']+self.message['heading']
        for i in bold_content:
            target = r'<p([^>]*)?><[^>]*>%s(<br>)?</[^>]*></p>' %self.escape_word(i)
            
            repl = '<%s>%s</%s>' %(self.heading, i, self.heading)#加了<p>反而出问题
            res = re.subn(target,repl,html)
            self._modify_warning(res[1],i)
            html = res[0]

        html = self._bold_names(html)
        self._change_html(body,html)
        self.driver.switch_to.parent_frame()
    
    def check_box(self,cover_num=1):
        pass
    
    def publish(self):
        button = self.find('.//footer//span[text()="立即发表"]')
        self._js_click(button)
        try:
            again = self._wait_for(1.5,(By.XPATH,'.//*[text()="文章检测"]/..//a[text()="直接发表"]'))
            # self._js_click(again)
            again.click()
        except TimeoutException:
            pass

    def _status(self,element):
        status = element.get_attribute('class')
        if 'wait' in status :
            return '待审核'
        elif 'delete' in status:
            return '已删除'
        else:
            return '已发表'
    
    def close_rank(self):
        try:
            rank = self._wait_for_displayed(2,(By.XPATH,'.//section[@class="f1_cm_info"]'))
            close = rank.find_element_by_xpath('.//a[@class="f1_cm_btn_clo"]')
            self._js_click(close)
        except TimeoutException:
            pass

    def _active_content(self):
        self._wait_for(1.5,(By.XPATH,'.//nav[@class="tab_nav"]//a')).click()

    def collect_info(self,title,next_page=True,read_count=False):
        
        self.driver.get(self.query_url)
        self.close_rank()
        try:
            essay_list = self._wait_for_all(1,(By.XPATH,'.//section[contains(@class,"feed_card")]'))
        except TimeoutException:
            if self.driver.current_url == self.query_url:
                self._active_content()
                
            else:
                self.driver.get(self.query_url)
            essay_list = self._wait_for_all(4,(By.XPATH,'.//section[contains(@class,"feed_card")]'))

        
        res = {}
        #time.sleep(1.5)#当title为空的时候，出现过将第二条新闻当作第一条处理，疑是页面载入出现问题
        for i in essay_list:
            # if '微博同步' in full_text:
            #     continue
            title_and_url = i.find_element_by_xpath('.//h2/a')
            full_title = title_and_url.text

            if '微博同步' in i.text:
                continue

            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发表':#防止出现微博转发在最后一条，但是在sina上发表的需要转到第二页
                    if next_page:
                        next_page=False
                        continue
                    else:
                        print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                        return res

                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                data = i.find_element_by_xpath('.//span[@class="con_b_s"]/em').text
                res['read_counts'] = self._strip_read_counts(data)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res
        else:
            if next_page:

                sbox = self._wait_for_clickable(3,(By.XPATH,'.//*[contains(@class,"search")]//input'))
                self.text_box(sbox,title)
                button = self.find('.//*[contains(@class,"search")]//a')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=False,read_count=read_count)
                
                else:
                    return {}
                # next_button = self.driver.find_elements_by_xpath('.//div[@class="page_num"]/a')[-1]#未测试
                # next_button.click()
                # return self.collect_info(title,next_page=False,start=start,read_count=read_count)
            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

    def check_published(self,url):
        if self.published_signal in url:
            return True
        else:
            self.driver.get(self.query_url)
            return False

######################搜狐##############################
class Sohu(Web):#翻页
    
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=True):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'strong'
        self.heading = 'h1'
        self.paras_tag = 'p'
        self.imgs_tag = 'img'
        self.body = './/div[@id="editor"]/div'   
        self.title_locator =  (By.XPATH,'.//input[contains(@placeholder,"请输入标题")]')
        self.published_signal = 'newsType'
        self.brand_path = os.path.join(current_path,'报告','info','brand-sohu.json')
        self.publish_url = 'https://mp.sohu.com/mpfe/v3/main/news/addarticle?contentStatus=1'
    
    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        qq_href = WebDriverWait(self.driver,20,0.5).until(EC.presence_of_element_located(\
                        (By.CSS_SELECTOR,'a[class="login-qq"]'))).get_attribute('href')

        self._qqlogin(qq_href,use,code)
 
    def paste(self,part):
        if part == 'title':
            self._paste_title()
            # title = self._wait_for(4,(By.XPATH,'.//input[@placeholder="请输入标题"]'))
            # self.delete_info(title)
            # title.send_keys(self.message['title'])
            # time.sleep(0.4)
        elif part == 'body':
            time.sleep(2)
            body_locator = (By.XPATH,'%s/p' %self.body)
            #body_locator = (By.XPATH,'.//div[@id="editor"]/div/p')
            self.ctrl_v(body_locator,self.intro)
        else:
            print('请输入"title"或者"body"。\n')
    
    def _check_imgs_load(self):
        path = self.body + '//' + self.imgs_tag
        self._wait_for_all(10,(By.XPATH,'%s' %path))
        path = self.body + '//' + 'div[@class="ql-image-place-error"]'
        failed_load_imgs = self.finds(path)
        if failed_load_imgs:
            input('%s中存在未能载入的%d张图片，请解决后回车。\n' %(self.source,len(failed_load_imgs)))
        # if len(imgs) != self.message['imgs_num']:
        #     ans  = input('%s中的图片载入不完全(手动调节后按回车继续，输入任意字母退出)\n' %self.source)
        #     if ans:
        #         raise Exception

    def _modify_content_html(self,html):
        for i in self.message['heading']:
            target = r'<%s([^>]*)?>%s(<br>)?</%s>' %(self.paras_tag,self.escape_word(i),self.paras_tag)
            
            repl = '<%s>%s</%s>' %(self.heading, i, self.heading)#加了<p>反而出问题
            res = re.subn(target,repl,html)
            self._modify_warning(res[1],i)
            html = res[0]

        for i in self.message['bold']:
            target = r'<p(?P<class>[^>]*?)>%s(\s)?(<br>)*?</p>' %self.escape_word(i)
            repl = r'<p\g<class>><%s>%s</%s></p>'  %(self.bold,i,self.bold)
            res = re.subn(target,repl,html)
            if self.message['source']!='tencent':#搜狐号继承腾讯文档的加粗字体
                self._modify_warning(res[1],i)
            html = res[0]
        return html
    
    def _hide_notes(self,times=3):
        path = self.body + '//' + self.imgs_tag + '/../span'
        for i in range(times):
            img_notes = self._wait_for_all(10,(By.XPATH,'%s' %path))
            if len(img_notes) >= self.message['imgs_num']:
                for i in img_notes:
                    self._hide_element(i)
                break
            else:
                time.sleep(2.5)
        else:
            Winhand().sonic_warn()
            ans = input('图片标注可能没有删除完毕，是否继续？（回车继续，按任意键退出）\n')
            
            if ans!='':
                raise Exception
    
    def _hide_notes_html_1(self,html):
        pattern_1 =  r'(?P<ori><img.+?><[^>]+)>'
        repel_1 = r'\g<ori> style="display:none">'
        res = re.subn(pattern_1,repel_1,html)
        html = res[0]
        

        

        return html

    def _hide_notes_html_2(self,html):
        pattern_2 = r'(?P<ori><span class="img-edit"[^>]+)>编辑<'
        repel_2 = r'\g<ori> style="display:none">编辑<'
        # repel_2 = r'\g<ori>><'
        
        res = re.subn(pattern_2,repel_2,html)
        #print(res[1])

        return res[0]

    def _hide_notes_ele(self,html):
        self._wait_for(3,(By.XPATH,'.//span[@class="img-edit"]'))


    def _delete_paras_attr(self,html):
        pattern = r'<p[^>]*>'
        repel = '<p>'
        html = re.sub(pattern,repel,html)
        return html

    def modify_content(self,exe=False):
        "双&nbsp;会保留，空格+&nbsp;或者&nbsp;+空格 会删除空格"
        "和头条一样"
        "strong标签回保留"
        "然而搜狐段落标签中含有属性，大部分平台不能继承"
        "搜狐继承腾讯文本的字体"
        if not exe:
            return 
        self._check_imgs_load()
        time.sleep(2)
        self._modify_blankspace(self.message['bold'])

        content  = self.find(self.body)
        html = self._get_tag_html(content)

        html = self.delete_extra_para(html)


        html = self._modify_content_html(html)#加粗小标题

        #html = self._delete_paras_attr(html)

        html = self._hide_notes_html_1(html)

        html = self._hide_notes_html_2(html)

        self._change_html(content,html)


        if self.message['source']=='weixin' and self.message['2Dcode']:
            Winhand().sonic_warn()
            input('请将第一张图片中的二维码截取再上传到对应位置(回车继续)\n')
        time.sleep(2)
        #self._hide_notes()

    def check_box(self,cover_num=1,again=True):
        #封面
        try:
            self.scroll_to_bottom()
            cover = self.find('.//*[contains(@class,"cover")]//*[contains(@class,"upload")]')
            self._js_click(cover)

            time.sleep(2)
            first_img = self._wait_for(2,(By.XPATH,'.//div[@class="content-images"]//img'))
            # ActionChains(self.driver).move_to_element_with_offset(first_img,50,50).pause(0.5).click().perform()
            time.sleep(0.5)
            self._js_click(first_img)

            time.sleep(0.5)
            button = self.find('.//div[@class="bottom-buttons"]/*[contains(@class,"positive")]')
            self._js_click(button)
        except Exception:
            print('%s封面设置出现异常\n' %self.source)
        # cover_set = self._wait_for(6,(By.XPATH,'.//div[@class="cover-area"]/span'))
        # cover_set.location_once_scrolled_into_view 

        #选择相关汽车品牌
        time.sleep(0.5)
        # anchor = self._wait_for_clickable(2,(By.XPATH,'.//div[@class="original-state"]//span[@class="check-box"]'))
        # anchor.location_once_scrolled_into_view
        self.scroll_to_bottom()
        branches = json.loads(open(self.brand_path).read())
        link_branch = ''
        for b in branches:
            for tag in self.message['tags']:
                if b in tag:
                    link_branch = b
                    break

        if link_branch:
            self._wait_for_clickable(2,(By.XPATH,'.//div[@class="plugin-dropdown"]//i[@class="arrow"]')).click()
            select_branch = self._wait_for_clickable(2,(By.XPATH,'.//ul[@class="drop-menu"]/li[contains(text(),"%s")]' %link_branch))
            select_branch.click()

        #文章属性
        self._wait_for_clickable(2,(By.XPATH,'.//div[@class="article-attr"]//div[text()="消息资讯"]')).click()

        #原创
        if self.message['original']:
            x_path = './/span[contains(text(),"原创声明")]/../*[contains(@class,"check")]'
            self._wait_for_clickable(2,(By.XPATH,x_path)).click()
        
    def publish(self):
        button = self.find('.//*[text()="发布"]')
        self._js_click(button)

    def _status(self,element):
        try:
            element.find_element_by_xpath('.//span[contains(@class,"status-text")]')
            return ''
        except NoSuchElementException:
            return '已发布'


    def collect_info(self,title,next_page=False,read_count=False,times=5):#搜索八页,50篇
        times-=1
        essay_list = self._wait_for_all(4,(By.XPATH,'.//div[@class="article-content-wrap"]/div[@class="article-content"]'))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath('.//*[@class="title"]/a')
            full_title = title_and_url.text
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                data = i.find_element_by_xpath('.//span[@class="status-view-icon"]/following-sibling::span[1]').text
                res['read_counts'] = self._strip_read_counts(data)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res
        else:
            if next_page:
                if times:
                    next_button = self.find('.//button[@class="go go-next"]')
                    self._js_click(next_button)
                    times-=1

                    time.sleep(1.5)
                    
                    if self.page_switch_test():
                        return self.collect_info(title,next_page=next_page,read_count=read_count,times=times)
                    else:
                        return {}
                else:
                    print('没有在%s中搜到所要的文章。\n' %self.source)

    def generate_branch_file(self):
        dir_path = self.brand_path

        self.scroll_to_bottom()

        self._wait_for_clickable(2,(By.XPATH,'.//div[@class="plugin-dropdown"]//i[@class="arrow"]')).click()
        branch_list_elements = self.finds('.//ul[@class="drop-menu"]/li')
        branches = []

        for i in branch_list_elements:
            branches.append(i.text[2:])

        if dir_path:
            if not os.path.exists(dir_path):
                print('由于所输入的路径不存在，正在生成一个该路径。\n')
                os.mkdir(dir_path)
                path = os.path.join(dir_path,'branch.json')
                finall_path = path
            
                
        else:
            path='branch.json'
            finall_path = os.path.join(os.getcwd(),path)
        with open(path,'w') as f:
            f.write(json.dumps(branches))
        
        print('文件保存在:\n%s' %finall_path)

######################网易##############################
class W163(Web):#搜索
    
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.heading='b'
        self.bold = 'b'
        self.body = './/div[@id="container"]'
        self.charct_b = 'p'
        self.charct_h = 'p'
        # if message:
        #     if self.message['source'] == 'tencent':
        #         self.charct_b = 'div'
        #         self.charct_h = 'div'
        #     elif self.message['source'] == 'weixin':
        #         self.charct_b = 'p'
        #         self.charct_h = 'p'
        self.title_locator = (By.XPATH,'.//input[@id="title"]')
        self.published_signal = 'manage'
        
    def is_login(self):
        try:
            self.driver.find_element_by_xpath('.//iframe')
            return False
        except NoSuchElementException:
            try:
                self._wait_for(1,(By.XPATH,'.//div/a[@id="dologin"]'))
                return False
            except TimeoutException:
                return True

    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        self.switch_to_frame()
        account = self._wait_for(4,(By.XPATH,'.//input[@placeholder="网易邮箱帐号"]'))
        self.delete_info(account)
        account.send_keys(use)
        psw = self.driver.find_element_by_xpath('.//input[@placeholder="密码"]')
        self.delete_info(psw)
        psw.send_keys(code)
        login = self.driver.find_element_by_xpath('.//div/a[@id="dologin"]')
        login.click()

        if self.is_login():
            print('登录成功。\n')
        else:
            Winhand().sonic_warn()
            input('有验证码，解决后回车继续。\n')
        try:
            login.click()
        except Exception:
            pass

    def _out_of_date(self,use,code):
        try:
            self.login(use,code)
            return True
        except TimeoutException:
            print('%s可能出现网络故障。\n' %self.source)
            return False

    def paste(self,part):#使用selenium登陆不容易出现上次文章载入的情况
        try:
            cancel = self._wait_for_displayed(1,(By.XPATH,'.//p[@class="auto-helper"]/a'))
            self._js_click(cancel)
            self._wait_for_invisible(3,(By.XPATH,'.//p[@class="auto-helper"]/a'))
        except TimeoutException:
            pass

        if part == 'title':
            self._paste_title()
            # title = self._wait_for(16,(By.XPATH,'.//input[@id="title"]'))
            # self.delete_info(title)
            # title.send_keys(self.message['title'])
        elif part == 'body':
            #body_locator = (By.XPATH,'.//div[@id="container"]/p')
            body_locator = (By.XPATH,'%s/p' %self.body)
            self.ctrl_v(body_locator,self.intro)
        else:
            print('请输入"title"或者"body"。\n')
    
    def get_content_html(self):
        if self.message['source'] == 'weixin':
            body = self.find(self.body)
            self.message['html'] = self._get_tag_html(body)
    
    def delete_extra_para(self):
        self._wait_for_all(15,(By.XPATH,'.//div[@id="container"]//img[@src]'))
        time.sleep(1)
        body = self.find(self.body)
        html = self._get_tag_html(body)
        for i in self.message['extras']:
            res = self.delete_para(html,self.charct_b,i)
            html = res[0]
        self._change_html(body,html)

    def copy(self):
        #需要等待
        #这种等待方式会复制全页
        if self.message['source']=='tencent':
            self.delete_extra_para()

        self._wait_for(20,(By.XPATH,'.//div[@id="container"]//img[contains(@src,"dingyue")]'))
        time.sleep(1)
        body_locator = (By.XPATH,'.//div[@id="container"]/p')
        self.ctrl_c(body_locator)

    def modify_content(self):
        "163只有加粗选项，加粗的标记是<b></b>，从微信拷贝过来的文章时段落全是扁平化的<p>text<//p>"
        "从腾讯文档拷贝过来的html是扁平的div结构，加粗方式与微信来的一样"
        "可以完美继承头条的字体"

        self._wait_for_all(15,(By.XPATH,'.//div[@id="container"]//img[@src]'))
        time.sleep(1)
        body = self.find(self.body)
        html = self._get_tag_html(body)
        html = self._modify_content_html(html,self.charct_b,self.charct_h,self.bold,self.heading)
        self._change_html(body,html)

    def _check_img_loaded(self,element):
        for i in range(20):
            int(i)
            is_ok = element.get_attribute('value')
            if is_ok:
                return True
            else:
                time.sleep(0.5)
        print('图片载入超时。\n')
                
    def _wait_for_img_list(self):
        img_list = self.find('.//div[@id="custom"]')
        for i in range(10):
            int(i)
            if 'active' in img_list.get_attribute('class'):
                return True
            else:
                time.sleep(0.3)
        print('图片选择面板载入超时。\n')
    
    def _select_img(self,num):
        img = self._wait_for(3,(By.XPATH,'.//div[@class="modal-content"]//div/img[@id="%d"]/../input' %num))
        self._js_click(img)
        button_1 = self.find('.//div[@class="modal-content"]//button[text()="确定"]')
        self._js_click(button_1)
        self._wait_for_displayed(5,(By.XPATH,'.//div[@class="modal-con"]//div[@class="cropper-wrap-box"]//img[contains(@src,"http")]'))
        time.sleep(1)
        button_2 = self._wait_for_displayed(3,(By.XPATH,'.//div[@class="modal-con"]//button[text()="确定"]'))
        time.sleep(0.5)
        self._js_click(button_2)

    def check_box(self,cover_num=1):
        self.scroll_to_bottom()
        "复制之后需要等待2秒才可以使用check_box"
        #选择汽车分类
        button = self._wait_for(4,(By.XPATH,'.//label[text()="分类"]/..//select/../div/button'))
        if button.get_attribute('title') != "汽车":
            self._js_click(button)
            time.sleep(0.3)
            ActionChains(self.driver).send_keys('汽车'+Keys.ENTER).perform()
        
        #选择三图模式或者自动
        if self.message['imgs_num'] >2:
            triple = self.find('.//label[text()="封面"]/..//label[text()="三图模式"]/..')
            self._js_click(triple)
            time.sleep(2)
            self._wait_for_displayed(2,(By.XPATH,'.//div[@data-pictype="1"]'))
            img_boxes = self._wait_for_all(2,(By.XPATH,'.//div[@data-pictype="1"]/div[@class="cover-img"]'))
            time.sleep(0.4)
            tri_boxes = []
            for box in img_boxes:
                if box.is_displayed():
                    target = box.find_element_by_xpath('.//img')
                    tri_boxes.append(target)
            for num,i in enumerate(tri_boxes):
                self._js_click(i)
                self._select_img(num)
                #确保完全载入
                if num<2:
                    time.sleep(1.5)

        else:
            single = self.find('.//label[text()="封面"]/..//label[text()="单图模式"]/..')
            self._js_click(single)
            img_boxes = self._wait_for_all(2,(By.XPATH,'.//div[@class="cover-img"]'))
            for box in img_boxes:
                if box.is_displayed():
                    target = box.find_element_by_xpath('.//img')
                    self._js_click(target)
                    break
            self._select_img(cover_num)

    def publish(self):
        first = self.find('.//button[contains(text(),"发布")]')
        self._js_click(first)
        second = self._wait_for(8,(By.XPATH,'.//div[@class="modal-content"]//div[@class="modal-footer"]/button'))
        self._js_click(second)

    def _status(self,element):
        return element.find_element_by_xpath('.//span[@class="state-tag"]').text

    def _strip_read_counts(self,data):
        counts = re.search(r'阅读：(?P<counts>\d+)',data).group('counts')
        return int(counts)

    def _title_and_url(self,element):
        try:
            title_and_url = element.find_element_by_xpath('./div[@class="card-title"]/span/a')
            return title_and_url
        except NoSuchElementException:
            title = element.find_element_by_xpath('./div[@class="card-title"]/span')
            return title

    def collect_info(self,title,next_page=False,start=0,read_count=False):#搜索两页，前40篇文章

        essay_list = self._wait_for_all(4,(By.XPATH,'.//div[@class="loading-box"]/div[@class="article-card"]'))

        res = {}
        for i in essay_list:
            title_and_url = self._title_and_url(i)
            full_title = title_and_url.text
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                data = i.find_element_by_xpath('./div[@class="data"]/span').text
                res['read_counts'] = self._strip_read_counts(data)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res

        else:
            if next_page and essay_list:

                sbox = self._wait_for_clickable(3,(By.XPATH,'.//*[contains(@class,"input-search")]//input'))
                self.text_box(sbox,title)
                button = self.find('.//*[contains(@class,"search")]//button')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=False,read_count=read_count)
                
                else:
                    return {}
                # next_button = self.find('.//button/span[text()="下一页"]/..')
                # next_button.click()
                # return self.collect_info(title,next_page=False,start=start,read_count=read_count)
            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

######################大鱼##############################
class Dayu(Web):#已基本完成，测试通过
    
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.heading = 'h1'
        self.bold = 'strong'
        self.body = './/body'
        self.title_locator = (By.XPATH,'.//div[@class="article-write_box-title"]/input')
        self.charct_b = 'p'
        self.charct_h = 'p'
        self.published_signal = 'contents'
        
    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        print('在selenium启动的模式下无法完成滑块操作。')

    def is_logged(self):
        self.driver.implicitly_wait(3)
        try:
            user = self._wait_for(2,(By.XPATH,'.//div[@class="name"]'))
            if user.text=="新汽车":
                return True
            else:
                return False
        except TimeoutException:
            print('%s首次登录没有成功。\n' %self.source)
            return False
        
    def paste(self,part):
        
        if part == 'title':
            self._paste_title()
            # title.send_keys(self.message['title'])
        elif part == 'body':
            self.switch_to_frame()
            #body_locator = (By.XPATH,'.//body/p')
            body_locator = (By.XPATH,'%s/p' %self.body)
            content = '<p><br></p>'
            body = self._wait_for(10,body_locator)
            self._change_html(body,content)
            self._wait_for(6,(By.XPATH,'.//body//p[@class="empty"]'))
            self.ctrl_v(body_locator,self.intro)
            self.driver.switch_to.parent_frame()
        else:
            print('请输入"title"或者"body"。\n')
    
    def wait_for_content(self):
        self._wait_for_invisible(20,(By.XPATH,'.//div[@class="ui-loading"]/i'))
        
        self.switch_to_frame()
        self._wait_for_displayed(15,(By.XPATH,'.//body//img[contains(@src,"dayu.com")]'))
        #print('图片载入完成。')
        self.driver.switch_to.parent_frame()

    def copy(self):
        #需要等待
        self.scroll_to_top()
        #print('执行完滑到顶部操作。')
        self.switch_to_frame()
        body_locator = (By.XPATH,'.//body/p')
        self.ctrl_c(body_locator)
        time.sleep(0.5)
        self.driver.switch_to.parent_frame()

    def modify_content(self):
        "从163修改格式后的复制来的html中加粗部分含有span，最好统一在一循环中修改"
        "如果文章来源于腾讯文档，从163不加修饰拷贝过来，是扁平的p格式"

        self.switch_to_frame()
        body = self.find(self.body)
        html = self._get_tag_html(body)
        if self.message['source']=='weixin':
            html = self.delete_empty_paras(html)
        #来自搜狐的文章不需要修改小标题
        # for i in self.message['heading']:
        #     target = r'<p[^>]*?>(<span>)?%s(\s)?(<br>)*?(</span>)?</p>' %self.escape_word(i)
        #     repl = '<%s>%s</%s>' %(self.heading,i,self.heading)
        #     res = re.subn(target,repl,html)
        #     self._modify_warning(res[1],i)
        #     html = res[0]

        for i in self.message['bold']:
            target = r'<p(?P<id>[^>]*?)>(<span>)?%s(\s)?(<br>)*?(</span>)?</p>' %self.escape_word(i)
            repl = r'<p\g<id>><%s>%s</%s></p>'  %(self.bold,i,self.bold)
            res = re.subn(target,repl,html)
            self._modify_warning(res[1],i)
            html = res[0]

        self._change_html(body,html)
        self.driver.switch_to.parent_frame()

    def select_img(self,i,num):
        button = i.find_element_by_xpath('.//button')
        ActionChains(self.driver).move_to_element(button).pause(0.3).click()
        imgs = self._wait_for_all(4,(By.XPATH,'.//div[@class="article-material-image_image-choose"]//i/..'))
        self._wait_for_clickable(4,(By.XPATH,'.//div[@class="article-material-image_image-choose"]//i/..'))
        imgs[num].click()
        self.find('.//div[@class="w-btn-toolbar"]/button[text()="下一步"]').click()
        self._wait_for(3,(By.XPATH,'.//div[contains(@class,"image")]/div[@class="w-btn-toolbar"]/button[text()="保存"]')).click()
    
    def check_auto_load_imgs(self,imgs_box):
        reset = False

        for i in imgs_box:
            try:
                i.find_element_by_xpath('.//img')
            except NoSuchElementException:
                reset = True
                break
        return reset
    
    def check_box(self,cover_num=1):
        self.scroll_to_bottom()
        #作者
        author = self._wait_for(6,(By.XPATH,'.//div[@id="author"]/input'))
        self.delete_info(author)
        author.send_keys(self.message['author'])

        #封面
        if self.message['imgs_num']<3:
            self._wait_for_clickable(2,(By.XPATH,'.//span[text()="单封面"]/../div')).click()
            #图片展示box中当载入图片后，会在与button上一级并列的地方出现一个img标签
            #当文中没有图片时，改位置是用来显示一个icon与“设置封面”的
            cover_select = self.find('.//div[@class="article-write-article-cover"]')
            self.select_img(cover_select,cover_num-1)

        else:
            self._wait_for_clickable(2,(By.XPATH,'.//span[text()="三封面"]/../div')).click()
            imgs_box = self._wait_for_all(8,(By.XPATH,'.//div[contains(@class,"normal-items")]/div'))
            reset = False
            selected_imgs = self._wait_for_all(8,(By.XPATH,'.//div[contains(@class,"normal-items")]//img[@src]'))
            if len(selected_imgs)!=3:
                reset = self.check_auto_load_imgs(imgs_box) 
                if reset:
                    for num,i in enumerate(imgs_box):
                        self.select_img(i,num)

        #推广微信
        radios = self.driver.find_elements_by_xpath('.//label[text()="其他设置"]/../div/div[contains(text(),"微信公众号")]/div[@class="w-radio"]')
        for i in radios:
            if i.is_displayed():
                i.click()

    def publish(self):
        self.find('.//div[@class="w-btn-toolbar"]//button[text()="发表"]').click()
        self._wait_for(4,(By.XPATH,'.//div[@class="article-write-preview_btn"]//button')).click()

    def _status(self,element):
        return element.find_element_by_xpath('.//span[contains(@class,"status")]').text

    def _strip_num(self,text):
        return int(re.search(r'阅读\s(\d*)',text).group(1))

    def _get_read_counts_and_screen_shot(self,url):
        self.open_new_window(url)
        target = self._wait_for(10,(By.XPATH,'.//div[@class="pages-article-opinion opinion-box"]'))
        screen_shot_path = self.screen_shot_for_element(target, bias=(0,0,0,400), y_scroll=-250)
        raw_txt = target.text
        pattern = r'阅读\s([^\s]+)'
        oral_num = re.search(pattern,raw_txt).group(1)

        num_pattern = r'(\d+)\.?(\d+)?([^\s]+)?'
        num_res = re.search(num_pattern,oral_num)
        
        if not num_res:
            print('%s解析文本失败\n' %self.source)
            return (-1, screen_shot_path)

        num_rear = num_res.group(2)#表示存在小数点
        if num_rear:
            num_fore = num_res.group(1)
            unit = num_res.group(3)
            if unit == '万':
                rate = 10000
            elif unit == '千':
                rate = 1000
            elif unit == '百万':
                rate = 1000000
            res = int(num_fore) * rate + int(num_rear)*rate/pow(10,len(num_rear))
            self.driver.close()
            return (int(res), screen_shot_path)

        else:
            self.driver.close()
            return (int(num_res.group(1)), screen_shot_path)

    def collect_info(self,title,next_page=False,read_count=False):#修改完毕
        essay_list = self._wait_for_all(4,(By.XPATH,'.//ul[@class="w-list"]/li[@class="w-list-item"]'))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath('.//h3/a')
            full_title = title_and_url.text
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                data_text = i.find_element_by_xpath('.//*[contains(@class,"analy")]').text#analyis-data拼错了
                #res['read_counts'] = self._strip_num(data_text)
                res['read_counts']  = -1

                if read_count:
                    print('%s暂不提供阅读量' %self.source)

                    #res['read_counts'],res['screen_shot_path'] = self._get_read_counts_and_screen_shot(res['url'])


                return res

        else:
            if next_page and essay_list:
                sbox = self._wait_for_clickable(3,(By.XPATH,'.//*[contains(@class,"search")]//input[@placeholder]'))
                self.text_box(sbox,title)
                button = self.find('.//*[contains(@class,"search")]//i[@class,"search"]')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=False,read_count=read_count)
                
                else:
                    return {}
                # try:#A计划
                #     next_button = self.find('.//i[@class="iconfont wm-icon-more1"]')
                # except NoSuchElementException:#B计划
                #     bottom_list = self.finds('.//div[@class="text-center"]//ul/li')
                #     next_button = bottom_list[-1].find_element_by_xpath('.//i')

                # next_button.click()
                # return self.collect_info(title,next_page=False,start=start,read_count=read_count)
            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

######################大风号##############################
class Ifeng(Web):#已基本完成，测试通过
    "从腾讯文档直接拷贝会使图文分离，图片会集中到最下面"
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'strong'
        self.heading = 'h1'
        #self.body = './/div[@id="editor"]/div'
        self.body = './/div[contains(@id,"editor")]//div[@contenteditable]'#虽然存在两个，但是第一个就是
        self.title_locator = (By.XPATH,'.//input[contains(@placeholder,"输入标题")]')
        self.published_signal = 'originalArticle'
    
    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        self._wait_for(3,(By.XPATH,'.//a[@id="btnSwapLogin"]')).click()

        self.get_into_frame()
        #qq登录界面的链接被加密，只能点击
        self.driver.find_element_by_xpath('.//a[@title="使用QQ号登录"]').click()
        current_handle = self.driver.current_window_handle
        self.search_new_window('QQ帐号')
        res = self._qqlogin(None,use,code)
        if res:
            self.driver.switch_to.window(current_handle)
            return res
            
        return res

    def paste(self,part,text=None):#无法输入introduce，可能是清空后，定位不在body上，
                                   #也有可能是清空后，需要停顿一定时间，才能send_keys
        if part == 'title':
            self._paste_title()

        elif part == 'body':
            body_locator = (By.XPATH,'%s/p' %self.body)
            self.ctrl_v(body_locator,self.intro)
        else:
            print('请输入"title"或者"body"。\n')
    
    def modify_content(self):
        pass
    
    def _wait_masks_invisual(self):
        masks  = self.finds('.//div[contains(@class,"modal_mask")]//div[text()="裁剪封面"]')
        ct = True
        for i in range(15):
            if ct:
                time.sleep(1)
            else:
                return True
            for j in masks:
                if j.is_displayed():
                    break
            else:
                ct=False
        else:
            return False

    def _check_img_chosen(self):
        img_set_windows = self.finds('.//div[contains(@class,"modal_title")]/div[text()="裁剪封面"]')
        for element in img_set_windows:
            try:
                self._wait_for_element_invisible(10,element)
            except TimeoutException:
                return

    def select_img(self,cover_num):
        self._wait_masks_invisual()
        add_img_button = self._wait_for(10,(By.XPATH,'.//p[text()="请添加封面"]'))
        self._js_click(add_img_button)
        imgs = self._wait_for_all(2,(By.XPATH,'.//*[@id="imgsList"]/div'))
        self._js_click(imgs[cover_num-1])
        select_1 = self.find('.//div[contains(@class,"modalContent")]//button[text()="确定"]')
        self._js_click(select_1)
        
        time.sleep(1.5)
        select_2 = self._wait_for(2,(By.XPATH,'.//div[contains(@class,"footer")]//button[text()="确定"]'))
        self._js_click(select_2)

        self._check_img_chosen()
        # imgs = self._wait_for_all(2,(By.XPATH,'.//div[text()="选择封面图"]/..//div[@class="publish-cover__list"]/div'))
        # self._js_click(imgs[cover_num-1])
        # select = self.find('.//div[text()="选择封面图"]/..//section[@class="publish-cover__btngroup"]/button[text()="确定"]')
        # self._js_click(select)
    
    def check_box(self,cover_num=1):
        self.scroll_to_bottom()
        #分类
        arrow = self.find('.//div[text()="分类"]/..//div[contains(@class,"arrow")]')
        self._js_click(arrow)
        select = self._wait_for(2,(By.XPATH,'.//ul[@style="display: block;"]/li[text()="汽车"]'))
        self._js_click(select)

        # s = self._wait_for(4,(By.XPATH,'.//select[contains(@class,"publish")]'))
        # Select(s).select_by_visible_text('汽车')

        #标签
        # tags_input = self._wait_for(2,(By.XPATH,'.//h3[text()="文章标签"]/../div/input[contains(@placeholder,"标签")]'))
        # max_len = len(self.message['tags'])
        # for num,i in enumerate(self.message['tags']):
        #     if num == max_len-1:
        #         message = i
        #     else:
        #         message = i + ' '
        #     tags_input.send_keys(message)

        #封面
        if self.message['imgs_num'] < 3:
            self.select_img(1)
            # single = self._wait_for(2,(By.XPATH,'.//h3[text()="文章封面"]/..//label[contains(text(),"单图")]/input'))
            # time.sleep(0.3)
            # ActionChains(self.driver).move_to_element(single).click().perform()
            # self._wait_for(2,(By.XPATH,'.//h3[text()="文章封面"]/..//div[contains(@class,"upload")]//a')).click()
            # self.select_img(cover_num)
        else:
            for i in range(3):
                self.select_img(i+1)
                time.sleep(1)
            # triple = self._wait_for(2,(By.XPATH,'.//h3[text()="文章封面"]/..//label[contains(text(),"三图")]/input'))
            # ActionChains(self.driver).move_to_element(triple).click().perform()
            # imgs_box = self._wait_for_all(2,(By.XPATH,'.//h3[text()="文章封面"]/..//div[contains(@class,"upload")]//a'))
            # for num,box in enumerate(imgs_box):
            #     time.sleep(0.4)
            #     self._js_click(box)
            #     time.sleep(0.4)
            #     self.select_img(num+1)
            #     if num<2:
            #         time.sleep(1.5)
        self.scroll_to_bottom()
        self.save_draft()

    def save_draft(self):
        "不保存的话，过一段时间再发布会出现正文图片链接过期的情况"
        draft = self.find('.//button[text()="保存草稿"]')
        self._js_click(draft)
        # self._wait_for(6,(By.XPATH,'.//div[text()="保存成功"]/..//a[text()="确定"]')).click()
        # print('%s草稿已保存\n' %self.source)

    def publish(self):
        p = self.find('.//button[text()="发布"]')
        self._js_click(p)
        # self._wait_for(3,(By.XPATH,'.//div[text()="发布成功"]/..//a[text()="确认"]')).click()

    def _int_str(self,text):
        fragment = text.split(',')
        data = ''
        for i in fragment:
            data+=i
        return int(data)

    def _status(self,element):
        try:
            status = element.find_element_by_xpath('.//p[@class="status "]').text
        except NoSuchElementException:
            status = element.find_element_by_xpath('.//p[@class="status warning"]').text
        return status

    def collect_info(self,title,next_page=False,read_count=False):#搜索两页，前40篇文章
        essay_list = self._wait_for_all(4,(By.XPATH,'.//table[@id="data-container"]/tbody/tr'))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath('.//div[@class="clearfix"]//p/a')
            full_title = title_and_url.text
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已上线':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))

                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                data = i.find_element_by_xpath('.//div[@class="data-box"]/span[contains(text(),"阅读")]').text
                res['read_counts'] = self._strip_read_counts(data)#以逗号分隔

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res

        else:
            if next_page and essay_list:

                next_button = self.find('.//li[@title="Next page"]')
                self._js_click(next_button)

                time.sleep(2)#不停顿会出现StaleElementReferenceException这个错误
                return self.collect_info(title,next_page=False,read_count=read_count)
            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

######################有车号##############################
class Youche(Web):#作为第一个粘贴对象已经基本完成，测试通过

    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'strong'
        self.heading = 'strong'
        self.body = './/body[@class="view"]'
        self.title_locator = (By.XPATH,'.//div[@class="artcle_title"]/input')
        self.locator = (By.XPATH,'.//iframe[contains(@id,"ueditor")]')
        self.charct_b = 'p'
        self.first_paste=True
        self.query_url = 'http://mp.youcheyihou.com/#/article-original'
    
    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        print('默认为%s自动保存了\n账号:%s\n密码:%s\n' %(self.source,use,code))
        Winhand().sonic_warn()
        input('请输入验证码，再点击登录。\n')
        print('%s正在重新激活发布链接...\n' %self.source)
        self.refresh_publish_url()

    def refresh_publish_url(self):
        "原有的句柄消失"
        current = self.driver.current_window_handle
        self._wait_for(6,(By.XPATH,'.//a[contains(text(),"原创文章")]')).click()
        time.sleep(2)
        new = self._wait_for(6,(By.XPATH,'.//a[text()="新建文章"]'))

        #伴随新页面弹出
        res = self.search_new_window(element=new)
        #self.driver.close()
        self.driver.switch_to.window(res)
        self._wait_for(5,(By.XPATH,'.//div'))
        time.sleep(1.5)
        self.driver.close()
        self.driver.switch_to.window(current)

    def paste(self,part):
        if part == 'title':
            self._paste_title()

        elif part == 'body':
            self.scroll_to_top()
            self.switch_to_frame(locator=self.locator)
            #body_locator = (By.XPATH,'.//body[@class="view"]/p')
            body_locator = (By.XPATH,'%s/p' %self.body)
            if self.first_paste:
                self.ctrl_v(body_locator,self.intro)
                self.first_paste = False
            else:
                self.ctrl_v(body_locator,None)
            self.driver.switch_to.parent_frame()
        else:
            print('请输入"title"或者"body"。\n')
    
    def delete_extra_para(self):
        time.sleep(1)
        body = self.find(self.body)
        html = self._get_tag_html(body)
        for i in self.message['extras']:
            res = self.delete_para(html,self.charct_b,i)
            html = res[0]
        self._change_html(body,html)

    def modify_content(self):
        pass

    def _wait_for_copy(self):

        self._wait_for_all(10,(By.XPATH,self.body + '//img'))
        time.sleep(1.5)

    def copy(self):
        self.scroll_to_top()
        try:
            self._wait_for(8,(By.XPATH,'.//div[text()="本地保存成功"]'))
            self._wait_for_displayed(8,(By.XPATH,'.//div[text()="本地保存成功"]'))
        except TimeoutException:
            pass
        locator = (By.XPATH,'.//iframe[contains(@id,"ueditor")]')
        self.switch_to_frame(locator=locator)
        self._wait_for_copy()
        #self.delete_extra_para()
        anchor = (By.XPATH,self.body + '/p')
        self.ctrl_c(anchor)
        self.driver.switch_to.parent_frame()
        
    def check_box(self,cover_num=1):
        if self.message['source'] == 'weixin':
            return 
        #封面
        self.scroll_to_top()
        select_big_cover = self._wait_for_clickable(5,(By.XPATH,'.//div[@class="article_cover"]//span[text()="大图模式"]/..//span[contains(@class,"input")]'))
        self._js_click(select_big_cover)
        boxes = self.driver.find_elements_by_xpath('.//div[@class="clearfix"]')
        for i in boxes:
            if i.is_displayed():
                i.find_element_by_xpath('.//input[contains(@id,"html")]').send_keys(self.message['cover_path'])

    def publish(self):
        if self.message['source'] == 'weixin':
            self.driver.close()
            return 
        try:
            self._wait_for(2,(By.XPATH,'.//div[@class="img_content"]'))
            self.find('.//div[@class="footer-main"]//button/span[text()="发布"]').click()
            self._wait_for(2,(By.XPATH,'.//div[@class="el-message-box"]//button[contains(@class,"primary")]')).click()
            try:
                same_article = self._wait_for_clickable(1.5,(By.XPATH,'.//div[@aria-label="重复文章提醒"]//div[@class="el-message-box__btns"]/button[contains(@class,"primary")]'))
                time.sleep(0.5)
                try:
                    same_article.click()
                except ElementClickInterceptedException:
                    time.sleep(2)
                    same_article.click()
            except TimeoutException:
                pass
        except TimeoutException:
            print('%s的图片未能正确载入。' %self.source)

    def _reopen_publish_window(self,pb_url,handles,again=True):
        
        if self.driver.current_url != pb_url:
            try:
                new_essay = self._wait_for(8,(By.XPATH,'.//a[text()="新建文章"]'))
                new_handle = self.search_new_window(element=new_essay)
                self.driver.close()
                handles['youcheyihou'] = new_handle
            except NoSuchElementException:
                self.driver.get(self.query_url)
                self._reopen_publish_window(pb_url,handles=handles,again=False)

    def _status(self,element):
        try:
            res = element.find_element_by_xpath('.//h3/span').text
        except NoSuchElementException:
            print('%s还没有被推荐。\n' %self.source)
            return ''
        return res

    def _strip_read_counts(self,data):
        res = re.search(r'(阅读)+\s*(?P<counts>\d+)',data).group('counts')
        return int(res)

    def _collect_url(self,title,page,start,times=5):
        ycyh_author_page = 'https://www.youcheyihou.com/mcn/media_260485490527129600'
        if page==1:
            self.open_new_window(ycyh_author_page)#打开并转到
        essay_list = self._wait_for_all(4,(By.XPATH,'.//div[@class="news-flow"]//ul/li'))
        for i in essay_list[start:]:
            title_of_li = i.find_element_by_xpath('.//h2').text
            if title in title_of_li:
                url = i.find_element_by_xpath('.//a[contains(@href,"/news/")]').get_attribute('href')
                self.driver.close()#返回前关闭
                return url
        else:
            if page<times:#前5页，一共60篇
                self.scroll_to_bottom()
                page += 1
                start+=15
                time.sleep(1)
                if self.page_switch_test():
                    return self._collect_url(title,page,start)
                else:
                    print('在%s的公开链接里\n' %self.source)
                    return ''

                
            else:
                print('%s没有搜到对应文章的链接。\n' %self.source)
                self.driver.close()
                return ''

    def collect_info(self,title,next_page=False,read_count=False):#搜索两页，前100篇文章
        if self.message['source']=='weixin':
            self.driver.get('http://mp.youcheyihou.com/#/article-sync')
            time.sleep(2)


        essay_list = self._wait_for_all(15,(By.XPATH,'.//ul[@class="article_list"]/li'))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath('.//h3/a')
            full_title = title_and_url.text
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已推荐':#没有被推荐就没有公开链接

                    #print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                    
                res['url'] = ''
                res['title'] = full_title
                data = i.find_element_by_xpath('.//div[@class="trc"]').text
                res['read_counts'] = self._strip_read_counts(data)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                try:
                    res['url'] = self._collect_url(title,page=1,start=0)
                except Exception:
                    print('########%s收集链接时出现错误:########' %self.source)
                    print(traceback.format_exc(),'\n')

                return res

        else:
            if next_page and essay_list:

                sbox = self._wait_for_clickable(3,(By.XPATH,'.//*[contains(@class,"search")]//input[@type="text"]'))
                self.text_box(sbox,title)
                button = self.find('.//*[contains(@class,"query")]//button')
                time.sleep(1)
                self._js_click(button)

                if self.page_switch_test():
                    time.sleep(3)

                    return self.collect_info(title,next_page=False,read_count=read_count)
                
                else:
                    return {}
                # button = self.find('.//button[@class="btn-next"]')
                # button.click()
                # return self.collect_info(title,next_page=False,start=start,read_count=read_count)
            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

######################趣头条##############################
class Qtt(Web):#搜索

    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'strong'
        self.heading = 'strong'
        self.body = './/body[@class="view"]' 
        self.paras_tag = 'p'
        self.title_locator = (By.XPATH,'.//div[@class="el-input"]/input[@placeholder]')
        self.published_signal = 'content-manage'
        self.query_url = 'https://mp.qutoutiao.net/content-manage/article?status=&page=1&title=&submemberid=&nickname=&start_date=&end_date=&isMotherMember=false'
    
    def is_login(self):
        if 'log' in self.driver.current_url:
            return False
        else:
            return True

    def login(self,use=None,code=None,first=False):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        print('dealing with qutoutiao....')
        login = WebDriverWait(self.driver,20,0.5).until(EC.presence_of_element_located(\
                        (By.ID,'submit-login')))
        if first:
            user = self.driver.find_element_by_css_selector('div[class="login"] input')
            self.delete_info(user)
            user.send_keys(use)
            pwd = self.driver.find_element_by_css_selector('div[class="login"] i[class^="pwd"] + input')
            self.delete_info(pwd)
            pwd.send_keys(code)
        login.click()

    def _wait_for_body(self,times=3):
        if times == 0:
            print('无法载入%s的正文部分。\n' %self.source)
            return False
        else:
            

            try:
                self._wait_for(3,(By.XPATH,'.//iframe'))#正文编辑页面
                return True
            except TimeoutException:
                self.driver.refresh()
                time.sleep(2)
                times -= 1
                self._wait_for_body(times=times)

    def paste(self,part):
        if not self.is_logged():
            self.login(self.use,self.code)
            pub = self._wait_for_clickable(5,(By.XPATH,'.//span[text()="内容发布"]'))
            self._js_click(pub)
            time.sleep(1.5)
        if part == 'title':
            if not self._wait_for_body():
                return
            try:
                time.sleep(0.8)
                exist_title = self.find('.//div[@class="tit-div"]')
                self._js_click(exist_title)
            except NoSuchElementException:
                pass
            self._paste_title()
            # title = self._wait_for(4,(By.XPATH,'.//div[@class="el-input"]/input[@placeholder]'))
            # self.delete_info(title)
            # title.send_keys(self.message['title'])
        elif part == 'body':
            self.switch_to_frame()
            body_locator = (By.XPATH,'%s/p' %self.body)
            self.ctrl_v(body_locator,self.intro)
            self.driver.switch_to.parent_frame()
        else:
            print('请输入"title"或者"body"。\n')
    
    def modify_content(self):
        "全文0级结构"
        "可以继承头条号的加粗，不能继承h1"
        self.switch_to_frame()
        body = self.find(self.body)
        html = self._get_tag_html(body)
        bold_and_heading = self.message['bold']+self.message['strong']#+self.message['heading']
        for i in bold_and_heading:
            target = r'<p>%s(<br>)?</p>' %self.escape_word(i)
            repl = '<p><%s>%s</%s></p>'  %(self.bold,i,self.bold)
            res = re.subn(target,repl,html)
            self._modify_warning(res[1],i)
            html = res[0]

        html = self._bold_names(html)
        self._change_html(body,html)
        
        self.driver.switch_to.parent_frame()
    
    def check_box(self,cover_num=1):
        self.scroll_to_bottom()

        #分类
        try:
            self._wait_for_clickable(4,(By.XPATH,'.//div[@class="cate-tag"]/a'))
            tags = self.driver.find_elements_by_xpath('.//div[@class="cate-tag"]/a')
            for tag in tags:
                self._js_click(tag)
        except TimeoutException:
            self.find('.//div[@class="selected-input"]//input[@placeholder]').click()
            try:
                self._wait_for_clickable(2,\
                    (By.XPATH,'//div[@role="tooltip"]//dt[text()="汽车"]/../dl[1]/dd[text()="汽车资讯" and @class!="selected"]')).click()
                self.driver.find_element_by_xpath(\
                    '//div[@role="tooltip"]//dt[text()="汽车"]/../dl[1]/dd[text()="车评" and @class!="selected"]').click()
                time.sleep(0.3)
                self.driver.find_element_by_xpath(\
                    '//div[@role="tooltip"]//dt[text()="汽车"]/../dl[1]/dd[text()="新车" and @class!="selected"]').click()
            except (TimeoutException,NoSuchElementException):
                pass
            #退出选择框
            classification = self.find('.//label[contains(text(),"分类")]')
            self._js_click(classification)
        #标签
        tag_input = self.find('.//div[@class="content-tag"]//input[@autocomplete]')
        for i in self.message['tags']:
            tag_input.send_keys(i+Keys.ENTER)
            time.sleep(0.3)
        
        #原创
        if self.message['original']:
            button = self.find('.//label[contains(text(),"原创")]/..//span[text()="是"]')
            self._js_click(button)

        #封面，自动生成
        if self.message['imgs_num'] > 2:
            triple = self._wait_for(20,(By.XPATH,'.//span[text()="三图"]/..//input'))
            self._js_click(triple)
            try:
                self._wait_for(10,(By.XPATH,'//label[contains(text(),"封面")]/..//img'))
            except TimeoutException:
                print('%s趣头条没有自动生成封面请自行解决\n' %self.source)

        else:
            single = self._wait_for(20,(By.XPATH,'.//span[text()="单图"]/..//input'))
            self._js_click(single)
            
            try:
                self._wait_for(10,(By.XPATH,'//label[contains(text(),"封面")]/..//img'))
            except TimeoutException:
                print('%s趣头条没有自动生成封面请自行解决\n' %self.source)
            #self._wait_for(3,(By.XAPTH,''))
            #相信网页可以选个好图

    def publish(self):
        p_button = self.find('.//div[@class="float-right"]//button/span[contains(text(),"发布")]/..')
        self._js_click(p_button)

        try:
            b_0 = self._wait_for_displayed(2,(By.XPATH,'.//div[@aria-label="发布提示"]//button[contains(@class,"primary")]'))
            time.sleep(0.3)
            b_0.click()
        except TimeoutException:
            pass
        try:
            b_1 = self._wait_for_displayed(3,(By.XPATH,'.//div[contains(@class,"dialog-personal-bind")]'))
            b_2 = b_1.find_element_by_xpath('.//input[@value="不再通知"]/..')
            self._js_click(b_2)
            
            b_3 = b_1.find_element_by_xpath('.//button/span[text()="关闭"]')
            self._js_click(b_3)
        except TimeoutException:
            pass
    
    def _reopen_publish_window(self,pb_url,handles,again=True):
        if self.driver.current_url != pb_url:
            try:
                new_essay = self._wait_for(8,(By.XPATH,'.//span[text()="发布内容"]'))
                self._js_click(new_essay)
            except NoSuchElementException:
                self.driver.get(self.query_url)
                self._reopen_publish_window(pb_url,handles,again=False)

    def _relog(self,title):
        self.driver.refresh()
        try:
            self._wait_for_all(4,(By.XPATH,'.//div[@class="content-list"]/div/div[@class="item"]'))
            self.collect_info(title)
        except TimeoutException:
            try:
                login = WebDriverWait(self.driver,2,0.5).until(EC.presence_of_element_located(\
                        (By.ID,'submit-login')))
                login.click()
                time.sleep(2)
                self.driver.get(self.query_url)
                self.collect_info(title)
            except TimeoutException:
                print('无法处理%s的文章查询界面。')
                return None

    def _int_str(self,text):
        fragment = text.split(',')
        data = ''
        for i in fragment:
            data+=i
        return int(data)

    def _status(self,element):
        return element.find_element_by_xpath('.//span[contains(@class,"reason-wrap")]').text

    def collect_info(self,title,next_page=False,read_count=False):
        if not self.is_logged():
            self.login()
            content = self._wait_for_clickable(5,(By.XPATH,'.//span[text()="内容管理"]'))
            self._js_click(content)
            time.sleep(1.5)
        try:
            essay_list = self._wait_for_all(4,(By.XPATH,'.//div[@class="content-list"]/div/div[@class="item"]'))
        except TimeoutException:
            self._relog(title)
        res = {}
        for i in essay_list:
            #链接必须点击
            title_and_url = i.find_element_by_xpath('.//div[@class="content-title"]/a')
            full_title = title_and_url.text
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                #res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                data = i.find_element_by_xpath('.//span[@class="data"]/span[contains(text(),"阅读")]').text
                res['read_counts'] = self._strip_read_counts(data)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                new_handle = self.search_new_window(element=title_and_url)
                self.driver.switch_to.window(new_handle)
                res['url'] = self.driver.current_url
                self.driver.close()
                return res

        else:

            if next_page and essay_list:

                sbox = self._wait_for_clickable(3,(By.XPATH,'.//*[contains(@class,"search")]//input'))
                self.text_box(sbox,title)
                button = self.find('.//*[contains(@class,"search")]//button')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=False,read_count=read_count)
                
                else:
                    return {}
                # auto_load = self.find('.//button[@class="btn-next"]/i')
                # auto_load.location_once_scrolled_into_view
                # start += 10

                # return self.collect_info(title,next_page=False,start=start,read_count=read_count)
            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

######################t头条号##############################
class Toutiao(Web):#搜索

    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'strong'
        self.heading = 'h1'
        self.body = './/div[@contenteditable]'   
        self.title_locator =   (By.XPATH,'.//textarea[contains(@placeholder,"文章标题")]')
        self.published_signal = 'articles'
        self.imgs_tag = 'img'#图片与纯文字段落并列的标签是div
        self.imgs_id = 'pgc-image'  #http://p9.pstatp.com/large/pgc-image/b0e5d284187047c296c1a4a2949eaf84
        self.paras_tag = 'p'
    
    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        print('dealing with toutiao....')
        try:
            self._wait_for_clickable(6,(By.XPATH,'.//img[contains(@class,"login")]')).click()
        except TimeoutException:
            pass
        self._wait_for_clickable(10,(By.XPATH,'//span[contains(text(),"帐密")]/../img')).click()#使用账号密码登录
        user = self._wait_for(6,(By.CSS_SELECTOR,'input[id="user-name"]'))
        self.delete_info(user)
        user.send_keys(use)
        pw = self._wait_for(6,(By.CSS_SELECTOR,'input[id="password"]'))
        self.delete_info(pw)
        pw.send_keys(code)

        self._wait_for_clickable(10,(By.XPATH,'.//button[text()="确定"]')).click()
        Winhand().sonic_warn()
        ans = input('请检查是否登录成功，如没有，请自行登陆(回车继续,按任意键退出)\n')
        if ans!=None:
            raise Exception

        #self.driver.find_element_by_xpath('//*[contains(text(),"发送验证码")]').click()
        #判断是否弹出验证码
        # time.sleep(0.5)
        # slide = self.driver.find_element_by_css_selector('div[id="pc_slide"]')
        # style = slide.get_attribute('style')
        # if style.split(':')[-1][1:-1] == 'none':
        #     input('Please input check code.')
 
    def paste(self,part):
        if part == 'title':
            self._paste_title()
            # title = self._wait_for(4,(By.XPATH,'.//input[@id="title"]'))
            # self.delete_info(title)
            # title.send_keys(self.message['title'])
        elif part == 'body':
            # body_xpath = self.body + '/p'
            # body_locator = (By.XPATH,body_xpath)
            body_locator = (By.XPATH,'%s/p' %self.body)
            self.ctrl_v(body_locator,self.intro)

            #self.copy()
        else:
            print('请输入"title"或者"body"。\n')
    
    def delete_mask_element(self,html):
        pattern_1 = r'<mask>.*?</mask>'#html中每张图存在两个<img>，一个隐藏，一个显示用来搜图编辑加说明等
        res = re.subn(pattern_1,'',html)
        if res[1]==0:
            raise Exception
        return res[0]

    def _modify_blankspace(self,txts):
        "删除空格+&nbsp;中的空格"
        for num,i in enumerate(txts):
            txts[num] = re.sub(r'\s+',' ',i)
        return txts

    def copy(self):
        if not self._wait_for_copy():
            Winhand().sonic_warn()
            ans = input('请手动重新载入后回车继续，按任意键退出')
            if ans:
                raise Exception

        content  = self.find(self.body)
        html = self._get_tag_html(content)

        html = self.delete_mask_element(html)

        self._change_html(content,html)
        time.sleep(1.5)
        self.scroll_to_top()


        anchor = (By.XPATH,self.body + '//' + self.paras_tag)
        self.ctrl_c(anchor)

    def _detect_empty_img(self):
        content = self.find(self.body)
        imgs = content.find_elements_by_xpath('.//img')
        empty_img = 0
        for i in imgs:
            rect = i.rect
            if rect['height']==16 and rect['width']==16:
                empty_img+=1
        if empty_img:
            Winhand().sonic_warn()
            ans = input('%s存在%d个图片没有载入（回车继续）\n' %(self.source,empty_img))

    def modify_content(self,exe=False):


        if not exe:

            self._detect_empty_img()
            return

        #修改双空格
        # bold = self.message['bold']

        # for num,i in enumerate(bold):
        #     bold[num] = re.sub(r'\s+',' ',i)
        self._modify_blankspace(self.message['bold'])
        content  = self.find(self.body)
        html = self._get_tag_html(content)


        html = self.delete_mask_element(html)

        html = self.delete_extra_para(html)

        html = self._modify_content_html(html, self.paras_tag, self.paras_tag, self.bold, self.heading)

        self._change_html(content,html)

        self._detect_empty_img()
        
        if self.message['source']=='weixin' and self.message['2Dcode']:
            Winhand().sonic_warn()
            input('请将第一张图片中的二维码截取再上传到对应位置(回车继续)\n')

    def check_box(self,cover_num=1):
        triple = self._wait_for(2,(By.XPATH,'.//span[text()="三图"]/..//input'))
        triple.location_once_scrolled_into_view
        #原创
        if self.message['original']:
            original = self._wait_for_clickable(4,(By.XPATH,'.//div[@id="originalBtn"]//span'))
            self._js_click(original)
            # confirm = self._wait_for_displayed(3,(By.XPATH,'.//div[contains(@class,"footer")]//button/span[contains(text(),"确定")]/..'))
            # self._js_click(confirm)
            cancel = self._wait_for(3,(By.XPATH,'.//span[contains(text(),"额外配置")]/..//input'))
            self._js_click(cancel)
        #图片
        if self.message['imgs_num'] > 2:
            #默认三图
            triple = self._wait_for(2,(By.XPATH,'.//span[text()="三图"]/..//input'))
            self._js_click(triple)
            # select = self._wait_for(2,(By.XPATH,'.//div[@class="article-cover-images"]/div/i'))
            # self._js_click(select)
            # imgs = self._wait_for_all(3,(By.XPATH,'.//main[@id="picture-main"]//div[@class="content"]//img'))
            # for i in imgs[:3]:
            #     self._js_click(i)
            # sure = self.find('.//main[@id="picture-main"]//div[@class="img-footer"]//button/span[text()="确认"]')
            # self._js_click(sure)
        else:
            single = self._wait_for(2,(By.XPATH,'.//span[text()="单图"]/..//input'))
            self._js_click(single)
            # select = self._wait_for(2,(By.XPATH,'.//div[@class="article-cover-images"]/div/i'))
            # self._js_click(select)
            # imgs = self._wait_for_all(3,(By.XPATH,'.//main[@id="picture-main"]//div[@class="content"]//img'))
            # self._js_click(imgs[cover_num-1])
            # sure = self.find('.//main[@id="picture-main"]//div[@class="img-footer"]//button/span[text()="确认"]')
            # self._js_click(sure)

    def publish(self):
        self.find('.//button[@id="publish"]').click()

    def _status(self,element):
        "有并列标签，需要分析"
        try:
            status = element.find_elements_by_xpath('.//div[@class="abstruct"]/*')
        except NoSuchElementException:
            return None
        for i in status:
            if '已发布' in i.text:
                return i.text

    def _strip_read_counts(self,data):#超过一万用万作为单位
        if '万' in data:
            res = re.search(r'(?P<ten_s>\d+).(?P<s>\d+)万',data)
            counts = int(res.group('ten_s'))*10000 + int(res.group('s'))*1000
        else:
            res = re.search(r'(?P<s>\d+)',data)
            counts  = int(res.group('s'))
        return counts

    def collect_info(self,title,next_page=False,read_count=False):#修改完毕
        essay_list = self._wait_for_all(4,(By.XPATH,'.//div[@class="article-card"]'))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath('.//div[@class="master-title"]/a')
            full_title = title_and_url.text
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                data = i.find_element_by_xpath('.//ul[@class="count "]/li[2]').text
                res['read_counts'] = self._strip_read_counts(data)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res

        else:
            if next_page and essay_list:

                sbox = self._wait_for_clickable(3,(By.XPATH,'.//*[contains(@class,"search")]//input'))
                self.text_box(sbox,title)
                button = self.find('.//*[contains(@class,"search")]//i[contains(@class,"search")]')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=False,read_count=read_count)
                
                else:
                    return {}

                # auto_load = self.find('.//div[@class="page"]//i[@class[contains(@class,"pagination-next")]]')
                # auto_load.location_once_scrolled_into_view
                # start += 10

                return self.collect_info(title,next_page=False,read_count=read_count)
            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

######################一点资讯##############################
class Ydzx(Web):#搜索
    
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'strong'
        self.heading = 'h1'
        self.body = './/div[@class="content"]//div[@role="textbox"]'
        self.title_locator = (By.XPATH,'.//div[@class="title"]/input')
        self.published_signal = 'ArticleManual'

    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        self._wait_for(2,(By.XPATH,'.//a[text()="登录"]')).click()

        account = self._wait_for(2,(By.XPATH,'.//input[@name="username"]'))
        self.delete_info(account)
        account.send_keys(use)

        password = self._wait_for(2,(By.XPATH,'.//input[@name="password"]'))
        self.delete_info(password)
        password.send_keys(code)

        log = self._wait_for(2,(By.XPATH,'.//button[text()="登录"]'))
        log.click()

    def paste(self,part):
        if part=='title':
            self._paste_title()
            # title = self._wait_for(4,(By.XPATH,'.//div[@class="title"]/input'))
            # self.delete_info(title)
            # title.send_keys(self.message['title'])
        elif part=="body":
            #body_locator = (By.XPATH,'.//div[@class="content"]//div[@role="textbox"]')
            body_locator = (By.XPATH,self.body)
            self.ctrl_v(body_locator,self.intro)
        else:
            print('请输入"title"或者"body"。\n')

    def modify_content(self):
        "一点资讯从大鱼拷贝过来的文章文中标题会传染到所有段落，故用加粗代替标题"
        body = self.find(self.body)
        html = self._get_tag_html(body)
        for i in self.message['heading']:
            target = r'<h1{1}(?P<id>[^>]*?)>%s(\s)?(<br>)*?</h1>{1}' %self.escape_word(i)
            repl = r'<p\g<id>><%s>%s</%s></p>'  %(self.bold,i,self.bold)
            html = re.sub(target,repl,html)

        self._change_html(body,html)

    def _select_img(self,num):
        if num>0:
        #前一个封面已经设置完毕
            self._wait_for(4,(By.XPATH,'.//div[@class="cover-setter"]/div[contains(@class,"cover-item setted")][%d]' %(num)))
        img_box = self._wait_for_displayed(4,(By.XPATH,'.//div[@class="cover-selector"]'))
        imgs = img_box.find_elements_by_xpath('.//img')
        self._js_click(imgs[num])
        self._wait_for_displayed(20,(By.XPATH,'.//div[contains(@class,"mp-crop-container")]//div[@class="pic"]'))
        time.sleep(0.3)
        button = self._wait_for_clickable(4,(By.XPATH,'.//div[contains(@class,"mp-crop-container")]//button[text()="裁切"]'))
        self._js_click(button)
        time.sleep(2)
    
    def _find_img_box(self):
        img_boxes = self._wait_for_all(4,(By.XPATH,'.//div[@class="cover-container"]/div[@class="cover-setter"]'))
        img_box = None
        for i in img_boxes:
            if i.is_displayed():
                img_box = i
        return img_box

    def check_box(self,cover_num=1):
        #原创
        self.scroll_to_bottom()
        if self.message['original']:
            origin  = self._wait_for_clickable(5,(By.XPATH,'.//span[@class="text" and contains(text(),"原创")]/../i'))
            self._js_click(origin)
            agree = self._wait_for_clickable(5,(By.XPATH,'.//div[@id="dialog"]//button[text()="同意"]'))
            self._js_click(agree)

        #封面
        if self.message['imgs_num'] > 2:
            triple = self._wait_for_clickable(4,(By.XPATH,'.//div[@class="article-cover-container"]//span[contains(text(),"三图")]/../i'))
            self._js_click(triple)
            img_box = self._find_img_box()

            imgs = img_box.find_elements_by_xpath('.//div[@class="mask"]')
            self._js_click(imgs[0])
            self._select_img(0)
            time.sleep(2)
            for i in range(1,3):
                nxt = self._wait_for(4,(By.XPATH,'.//div[@class="cover-item active"]/div'))
                self._js_click(nxt)
                self._select_img(i)
        else:
            single = self._wait_for_clickable(4,(By.XPATH,'.//div[@class="article-cover-container"]//span[contains(text(),"单图")]/../i'))
            self._js_click(single)
            img_box = self._find_img_box()
            imgs = img_box.find_elements_by_xpath('.//div[@class="mask"]')
            self._js_click(imgs[0])
            self._select_img(cover_num-1)

    def publish(self):
        self.find('.//div[contains(@class,"footer")]/*[text()="发布"]').click()
        box = self._wait_for_displayed(4,(By.XPATH,'.//div[@class="dialog warning showDialogBody"]'))
        time.sleep(1)
        box.find_element_by_xpath('.//button[text()="确定"]').click()

    def _int_str(self,text):
        fragment = text.split(',')
        data = ''
        for i in fragment:
            data+=i
        return int(data)

    def _status(self,element):
        return element.find_element_by_xpath('.//p[@class="tags"]/span').text

    def collect_info(self,title,next_page=False,read_count=False):#修改完毕
        essay_list = self._wait_for_all(4,(By.XPATH,'.//div[@class="articleList"]/div[@class="article"]'))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath('.//h4/a')
            full_title = title_and_url.text
            #print(full_title)
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                data = i.find_element_by_xpath('.//div[@class="datas"]/span[contains(text(),"阅读")]').text
                res['read_counts'] = self._strip_read_counts(data)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res

        else:
            if next_page and essay_list:

                sbox = self._wait_for_clickable(3,(By.XPATH,'.//*[contains(@class,"search")]//input'))
                self.text_box(sbox,title)
                button = self.find('.//*[contains(@class,"search")]//div[@class="icon"]')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=False,read_count=read_count)
                
                else:
                    return {}

                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

######################车家号##############################
class Cjh(Web):#搜索 完全不能继承头条的格式
    
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'b'
        self.heading = 'h2'
        self.body = './/div[@id="editor"]/div' 
        self.paras_tag = 'p'
        self.title_locator = (By.XPATH,'.//div[@class="ipt_title"]/input')
        self.intro_locator = (By.XPATH,'.//div[@class="textre_txt"]/textarea[@name="intro"]')
        self.introduce_exist=True
        self.published_signal = 'Info?'

    def login(self,use=None,code=None):#登陆按钮无法处理
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        print('%s请自行登录\n' %self.source)
        print('%s的帐号:%s\n\t密码:%s' %(self.source,self.use,self.code))

    def _first_para_check(self):
        "车家号第一段在复制前不可以是图片。"
        first_para = self.find('.//div[@id="editor"]/div/*')
        if first_para.tag_name == 'p':
            return True
        else:
            return False
    
    def _switch_to_publish_page(self,again=True):#转到并黏贴
        time.sleep(1.5)
        publish = self.find('.//a[contains(@href,"AuthorArticles")]')#'.//div[@class="menuB"]/a[contains(@href,"AuthorArticles")]'
        self._js_click(publish)
        try:
            self._wait_for(6,(By.XPATH,self.body))
        except TimeoutException:
            if again:

                self._switch_to_publish_page(again=False)
            else:
                print('####%s第二次转入发布界面没有成功\n' %self.source)

    def _paste_cjh_title(self,again=True):
        title = self._wait_for(10,self.title_locator)
        self.delete_info(title)
        title.send_keys(self.message['title'])
        time.sleep(0.5)

        intro = self._wait_for(10,self.intro_locator)
        self.delete_info(intro)
        intro.send_keys(self.message['introduce'])


        # self._paste_title()

        # time.sleep(0.3)
        # self._paste_intro()

    def _paste_cjh_body(self,again=True,check=True):
        if check:
            dst = 'https://chejiahao.autohome.com.cn/My'
            current_url = self.driver.current_url
            if current_url==dst:
                self.refresh()
                self._switch_to_publish_page()
            else:
                if again:
                    self.driver.get(dst)
                    self._paste_cjh_body(again=False)
                return


        if not self._first_para_check():
            Winhand().sonic_warn()
            res = input('%s第一段不是文字，请在原窗口重新修改后回车(按任意键结束)' %self.source)
            if res != '':
                raise EnvironmentError

        body_locator = (By.XPATH,'.//div[@id="editor"]/div/p')
        # try:
        #     self.ctrl_v(body_locator,self.intro)
        # except UnexpectedAlertPresentException:
        #     self.ctrl_v(body_locator,self.intro)
        time.sleep(2)
        self.scroll_to(100)
        self.ctrl_v(body_locator,self.intro)

    def paste(self,part,again=True,check=True):
        if part != 'body':
            return
        self.driver.set_page_load_timeout(6)
        try:

            self._paste_cjh_body(check = check)#需要这个函数中的点击按钮的功能
            self._paste_cjh_title()
            
            time.sleep(1)
            self.scroll_to_top()
        except Exception:
            if again:
                print('%s黏贴正文第一次尝试失败\n' %self.source)
                self.driver.refresh()
                self.paste(part=part,again=False,check=False)
            else:
                print('%s黏贴正文第二次尝试失败\n' %self.source)
                self.driver.set_page_load_timeout(20)
        
    def _modify_bold(self):
        new_bold = []

        for i in self.message['bold']:
            text = self._np_modify(i)
            if text:
                new_bold.append(text)
            else:
                new_bold.append(i)

        return new_bold

    def _wait_for_copy(self):
        self._wait_for_all(15,(By.XPATH,self.body + '//img'))
        time.sleep(1.5)
    
    def delete_extra_para(self):
        time.sleep(1)
        body = self.find(self.body)
        html = self._get_tag_html(body)
        for i in self.message['extras']:
            res = self.delete_para(html,self.paras_tag,i)
            html = res[0]
        self._change_html(body,html)

    def copy(self):
        self.scroll_to_top()
        self.delete_extra_para()
        self._wait_for_copy()
        anchor = (By.XPATH,self.body + '/p')
        self.ctrl_c(anchor)

    def modify_content(self):#对于一个空格加&nbsp;的双空格，车家号会删去空格，保留一个&nbsp;
        '车家号正文的html格式非常固定，与来源关系不大'
        #self._paste_cjh_title()#将黏贴标题放在这一步
        body = self.find(self.body)
        html = self._get_tag_html(body)

        html = self.delete_introduce(html,'p')

        
        bold_text = self._modify_bold()
        for i in bold_text:
            target = r'<%s>%s(<br>)?</%s>' %(self.paras_tag,self.escape_word(i),self.paras_tag)
            repl = '<%s><%s>%s</%s></%s>'  %(self.paras_tag,self.bold,i,self.bold,self.paras_tag)
            res = re.subn(target,repl,html)
            self._modify_warning(res[1],i)
            html = res[0]

        for i in self.message['strong']:
            target = r'<%s>%s(<br>)?</%s>' %(self.paras_tag,self.escape_word(i),self.paras_tag)
            repl = '<%s><%s>%s</%s></%s>'  %(self.paras_tag,self.bold,i,self.bold,self.paras_tag)
            res = re.subn(target,repl,html)
            self._modify_warning(res[1],i)
            html = res[0]

        for i in self.message['heading']:
            target = r'<%s>%s(<br>)?</%s>' %(self.paras_tag,self.escape_word(i),self.paras_tag)
            repl = '<%s>%s</%s>'  %(self.heading, i, self.heading)
            res = re.subn(target,repl,html)
            self._modify_warning(res[1],i)
            html = res[0]

        html = self._bold_names(html)
        
        self._change_html(body,html)

    def delete_fisrt_para(self,html):
        i = 1
        while True:
            first_para = self.find('.//div[@id="editor"]/div//p[%d]' %i)
            if first_para.text:
                sp_introduce_html = self._get_tag_html(first_para)
                sp_introduce = self._get_text_from_html(sp_introduce_html)
                print('第二次删除的导语为:%s\n' %sp_introduce)
                res = self.delete_para(html,self.paras_tag,sp_introduce)
                if res[1]:
                    print('%s的导语第二次删除成功。' %self.source)
                else:
                    print('#####%s的导语第二次删除没有成功' %self.source)
                return res[0]
            else:
                i += 1
    
    def _warning_for_cover(self):
        try:
            warning = self._wait_for_displayed(2,(By.XPATH,'.//div[contains(@class,"alert-layer")]//div[@class="text-wrapper"]'))
            print('%s页面警告为:\n%s\n' %(self.source,warning.text))
        except TimeoutException:
            print('%s图片上传出现问题。\n' %self.source)

    def _change_cover_size(self,target_size =  (560,315)):
        img  = CompressImage(self.message['cover_path'])
        if img.size[0] < target_size[0] or img.size[1] < target_size[1]:
            return img.extendMargin(target_size,'autohome')
        else:
            return self.message['cover_path']

    def check_box(self,cover_num=1):
        #封面
        cover_path = self._change_cover_size()
        element = self._wait_for(4,(By.XPATH,'.//img[@id="imgcover"]/..'))

        self._load_cover(element,again=True,img_path = cover_path,js_click=False)

        
        #等待成功上传
        try:
            self._wait_for(6,(By.XPATH,'.//img[@id="imgcover" and contains(@src,"c")]'))
        except TimeoutException:
            self._warning_for_cover()

        #原创
        if self.message['original']:
            self.find('.//div[@id="chkIsOriginal"]/i').click()

    def publish(self):
        self.find('.//a[text()="发布"]').click()

    def _int_str(self,text):
        fragment = text.split(',')
        data = ''
        for i in fragment:
            data+=i
        return int(data)

    def _status(self,element):
        return element.find_element_by_xpath('.//div[@class="width1347"]').text

    def _get_reason(self,element):
        "<div...>审核未通过<div...>原因</div></div> 这种格式无法通过ele.text获取文字"
        html = self._get_tag_html(element)
        target = r'<div class="resultNo">(.*?)</div>'
        try:
            res = re.search(target,html).group(1)
        except AttributeError:
            return []
        return res

    def collect_info(self,title,next_page=False,read_count=False):#修改完毕
        essay_list = self._wait_for_all(4,(By.XPATH,'.//div[@class="table-list"]/div[@class="list-div"]'))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath('.//div[@class="list-div-content-title"]/a')
            full_title = title_and_url.text
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if not(status == '已发布' or status == '推荐中'):
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    reason = self._get_reason(i)
                    if reason:
                        print('%s没有过审的原因:%s' %(self.source, reason))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                data = i.find_element_by_xpath('.//i[@title="浏览量"]/../span').text
                res['read_counts'] = self. _int_str(data)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res

        else:
            if next_page and essay_list:

                sbox = self._wait_for_clickable(3,(By.XPATH,'.//*[contains(@class,"search")]//input'))
                self.text_box(sbox,title)
                button = self.find('.//*[contains(@class,"search")]//*[contains(@id,"btn")]')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=False,read_count=read_count)
                
                else:
                    return {}

                # auto_load = self.find('.//div[@class="pagination"]/li/a[@data-page-index="%d"]' %2)
                # auto_load.location_once_scrolled_into_view

                # return self.collect_info(title,next_page=False,read_count=read_count)
            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

######################车友号##############################
class Cheyou(Web):#翻页查找

    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'b'
        self.heading = 'b'
        self.body = './/div[@contenteditable and @id]'  
        self.title_locator =  (By.XPATH,'.//input[@name="title"]')
        self.published_signal='article'
    
    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        print('%s请自行登录\n' %self.source)
        print('%s的帐号:%s\n\t密码:%s' %(self.source,self.use,self.code))

    def paste(self,part):
        if part == 'title':
            self._paste_title()
            # title = self._wait_for(4,(By.XPATH,'.//input[@name="title"]'))
            # self.delete_info(title)
            # title.send_keys(self.message['title'])
        elif part == 'body':
            #body_locator = (By.XPATH,'.//div[@contenteditable and @id]/p')
            body_locator = (By.XPATH,'%s/p' %self.body)
            self.ctrl_v(body_locator,self.intro)
        else:
            print('请输入"title"或者"body"。\n')

    def modify_content(self):
        #只需要处理加粗部分，从大鱼修改过的文本是<p><span>文本<\span><\p>

        body = self.find(self.body)
        html = self._get_tag_html(body)
        for i in self.message['bold']:
            target = r'<p><[^>]*?>{1}?%s</.*?></p>{1}?' %self.escape_word(i)
            repl = '<p><%s>%s</%s></p>'  %(self.bold,i,self.bold)
            html = re.sub(target,repl,html)
        self._change_html(body,html)

    def check_box(self,cover_num=1):
        self.scroll_to_bottom()
        #分类
        clf = self._wait_for(20,(By.XPATH,'.//label[text()="分类设置"]/..//div[@data-name="channel"]/label'))
        if clf.text!="新车":
            self._js_click(clf)
            lst = self._wait_for_displayed(5,(By.XPATH,'.//ul[@class="select-list"]'))
            tgt = lst.find_element_by_xpath('./li[text()="新车"]')
            self._js_click(tgt)

        #封面
        if self.message['imgs_num'] > 2:
            triple = self._wait_for(3,(By.XPATH,'.//label[text()="封面设置"]/..//label[contains(text(),"三图")]/input'))
            self._js_click(triple)
            self._wait_for_displayed(10,(By.XPATH,'.//div[contains(@class,"fengmian-select")]//img'))
            imgs = self._wait_for_all(10,(By.XPATH,'.//div[contains(@class,"fengmian-select")]//img'))
            for i in imgs[:3]:
                self._js_click(i)
        else:
            single = self._wait_for(1,(By.XPATH,'.//label[text()="封面设置"]/..//label[contains(text(),"单图")]/input'))
            self._js_click(single)
            self._wait_for_displayed(10,(By.XPATH,'.//div[contains(@class,"fengmian-select")]//img'))
            imgs = self._wait_for_all(10,(By.XPATH,'.//div[contains(@class,"fengmian-select")]//img'))
            self._js_click(imgs[cover_num-1])

    def publish(self):
        self.find('.//button[text()="发布"]').click()
        self._wait_for(5,(By.XPATH,'.//div[@class="dialog-main "]//button[text()="确定"]')).click()

    def _status(self,element):
        res = element.find_element_by_xpath('.//p[@class="desc"]/span').text
        start = res.rfind(' ')+1
        return res[start:]

    def collect_info(self,title,next_page=False,read_count=False,endless=False):#搜索两页，前20篇文章
        essay_list = self._wait_for_all(4,(By.XPATH,'.//ul/li[@class="cl"]'))
        res = {}
        
        for i in essay_list:
            contain_link = True
            try:
                title_and_url = i.find_element_by_xpath('.//h3/a')
            except NoSuchElementException:
                title_and_url = i.find_element_by_xpath('.//h3')
                contain_link = False
            full_title = title_and_url.text
            if title in full_title:
                if not contain_link:
                    print('%s号文章暂无链接\n' %self.source)
                    return res

                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                data = i.find_element_by_xpath('.//p[@class="static"]').text
                res['read_counts'] = self._strip_read_counts(data)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res

        else:
            if next_page:
                self.scroll_to_bottom()
                button = self.find('.//a[text()="下一页"]')
                self._js_click(button)
                next_page = False

                if self.page_switch_test():

                    if endless:
                        next_page = True

                    return self.collect_info(title,next_page=next_page,read_count=read_count,endless=endless)
                
                else:
                    return {}

            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

######################知乎号##############################     
class Zhihu(Web):#发布已测试完成
    
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'b'
        self.heading = 'b'
        self.body = './/div[@contenteditable]/div[@data-contents]'
        self.title_locator =  (By.XPATH,'.//textarea[@placeholder]')
        self.published_signal='/p/'

    def is_logged(self,again=True):
        try:
            if self.message['model'] == 'publish':
                self._wait_for(4,(By.XPATH,'.//*[text()="写文章"]'))
            else:
                self._wait_for(4,(By.XPATH,'.//*[text()="帮宁工作室"]'))

            return True
        except TimeoutException:
            self.driver.refresh()
            if again:
                return self.is_logged(again=False)
            else:
                print('\n%s首次登录没有成功。\n' %self.source)
                return False

    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        print('%s无法在selenium控制界面登陆。' %self.source)

    def paste(self,part):
        if part == 'title':
            self._paste_title()

        elif part == 'body':
            #body_locator = (By.XPATH,'.//div[@contenteditable]/div[@data-contents]/div')
            body_locator = (By.XPATH,'%s/div' %self.body)
            self.ctrl_v(body_locator,self.intro)
        else:
            print('请输入"title"或者"body"。\n')

    def modify_content(self):
        pass

    def check_box(self):
        #上传封面
        self.scroll_to_top()
        cover = self._wait_for(2,(By.XPATH,'.//input[contains(@accept,"png")]'))
        cover.send_keys(self.message['cover_path'])
        #检查图片是否上传
        try:
            self._wait_for(5,(By.XPATH,'.//div[@class="WriteTitleImage"]/img[contains(@src,"https")]'))
        except TimeoutException:
            print('%s的封面设置失败。' %self.source)

        #获取知乎自动生成的tags，并与知乎的文章绑定
        last_tags = self.get_tags() + self.message['tags']
        cache = []
        for i in last_tags:
            if i not in cache:
                cache.append(i)
            
        
        if len(cache) > 4:
            self.message['tags'] = cache[:5]
        else:
            self.message['tags'] = cache

    def get_tags(self):
        button = self.find('.//div[@class="PublishPanel-wrapper"]/button')
        button.click()
        tags = []
        tag_element = self.finds('.//div[@class="PublishPanel-popover"]//ul[contains(@class,"tag")]/li')
        for i in tag_element:
            tags.append(i.find_element_by_xpath('.//a[contains(@class,"tagLink")]').text)



        return tags

    def _choose_tags(self):
        "貌似这样不是为了添加tag，是取消tag"
        locator = './/div[@class="PublishPanel-popover"]//ul[contains(@class,"tag")]/li'
        judge = lambda x:self.find_with_no_error(locator)
        for i in range(10):
            tag_element = judge(0)
            if tag_element:
                tag_element.click()
                time.sleep(1.2)
            else:
                break
        del i

    def check_published(self,url):
        if 'edit' in url:
            return False
        else:
            return True

    def publish(self,again=True):
        
        try:
            next_step = self._wait_for(2.5,(By.XPATH,\
                './/div[@class="PublishPanel-popover"]//button[text()="下一步"]'))
            time.sleep(0.8)
            next_step.click()
        except TimeoutException:
            button = self.find('.//div[@class="PublishPanel-wrapper"]/button')
            self._js_click(button)
            if again:
                return self.publish(again=False)
            else:
                print('%s没有发布时没有出现下拉弹窗\n' %self.source)
                return

        try:
            skip = self._wait_for(1.5,(By.XPATH,'.//div[@class="Modal-inner"]//button[text()="暂不开通"]'))
            time.sleep(0.8)
            skip.click()
        except TimeoutException:
            pass
        
    def collect_info(self,title,next_page=False,start=0,read_count=False):
        #由于知乎对selenium有屏蔽效应，所以不能直接访问主页

        essay_list = self._wait_for_all(4,(By.XPATH,'.//div/div[@class="List-item"]'))
        res = {}
        for i in essay_list[start:]:
            title_and_url = i.find_element_by_xpath('.//h2/a[contains(@href,"/p/")]')
            full_title = title_and_url.text
            if title in full_title:
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title

                res['read_counts'] = -1

                # if read_count:
                #     res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res

        else:
            if next_page:
                self.scroll_to_bottom()
                next_button = self.find('.//button[text()="下一页"]')
                time.sleep(0.8)
                next_button.click()
                return self.collect_info(title,next_page=False,start=0,read_count=read_count)
            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

#####################企鹅号##############################
class Qq(Web):
    
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.query_url = 'https://kuaibao.qq.com/s/MEDIANEWSLIST?chlid=6188308&refer='
    
    def is_logged(self):
        return True
        # try:
        #     self._wait_for(2,(By.XPATH,'.//*[@id="articlelist"]'))
        #     return True
        # except TimeoutException:
        #     print('%s首次登录没有成功。\n' %self.source)
        #     return False
    
    def _status(self,element):
        return element.find_element_by_xpath('.//span[contains(@class,"text-status")]').text

    def collect_info_1(self,title,next_page=True,start=0,read_count=False):#搜索两页，前20篇文章
        if self.driver.current_url==self.query_url:
            content = self._wait_for(4,(By.XPATH,'.//a[text()="我的内容"]'))
            self._js_click(content)
        essay_list = self._wait_for_all(4,(By.XPATH,'.//ul[@class="article-list"]/li[@class="article-item"]'))
        res = {}
        for i in essay_list[start:]:
            title_and_url = i.find_element_by_xpath('.//h4/a')
            full_title = title_and_url.text
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                #data = i.find_element_by_xpath('.//i[@title="浏览量"]/../span').text
                res['read_counts'] = 0
                return res

        else:
            if next_page:
                self.scroll_to_bottom()
                #next_button = self.find('.//li[@title="Next page"]')
                #next_button.click()
                self.collect_info_1(title,next_page=False)
            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}

    def collect_info(self,title,read_count=False,next_page=False):
        if self.driver.current_url==self.query_url:
            self.driver.get(self.query_url)
        essay_list = self._wait_for_all(4,(By.XPATH,'.//*[@data-index]'))
        res = {}
        for i in essay_list:
            full_title = i.text
            if title in full_title:
                res['title'] = re.search(r'(\n)?(?P<target>.*%s.*)\n' %title,full_title).group('target')
                i.location_once_scrolled_into_view
                self._js_click(i)
                time.sleep(1)
                res['url'] = re.search(r'(http.*?)(\?refer=)?$',self.driver.current_url).group(1)
                self.driver.back()
                res['read_counts'] = -1
                res['status'] = 1
                if read_count:
                    print('企鹅号无法提供阅读量信息。\n')
                
                return res
        else:
            print('没有在%s中搜到所要的文章。\n' %self.source)
            return {}
            
    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code
        log_box = self._wait_for(4,(By.XPATH,'.//div[@class="login-type-qq"]/img'))
        self._js_click(log_box)
        self.switch_to_frame()
        self.switch_to_frame()
        acct_and_psw = self._wait_for_displayed(4,(By.XPATH,'.//div[@id="bottom_qlogin"]//a[text()="帐号密码登录"]'))
        self._js_click(acct_and_psw)

        login = self._wait_for(2,(By.XPATH,'.//input[@id="login_button"]'))
        account = self.driver.find_element_by_id("u")
        self.delete_info(account)
        account.send_keys(use)

        pwd = self.driver.find_element_by_css_selector("input[type='password']")
        self.delete_info(pwd)
        pwd.send_keys(code)
        time.sleep(0.3)
        login.click()
        try:
            self._wait_for_all_displayed(4,(By.XPATH,'.//div[@id="newVcodeArea"]'))
            print('%s出现验证码，请处理。\n' %self.source)
            self._wait_for_invisible(30,(By.XPATH,'.//div[@id="newVcodeArea"]'))
        except TimeoutException:
            pass
        if self.is_logged():
                print('%s登录成功!\n' %self.source)
                return True
        else:
            return False
        # self.driver.switch_to.parent_frame()
        # self.driver.switch_to.parent_frame()

######################太平洋号##############################
class Tpy(Web):
    "不能直接获取微信文章中的图片"
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'strong'
        self.heading = 'strong'
        self.paras_tag = 'p'
        self.imgs_tag = 'img'
        self.body = './/body'
        self.locator = (By.XPATH,'.//iframe[contains(@class,"edit")]')
        self.title_locator =  (By.XPATH,'.//input[@placeholder and contains(@id,"title")]')
        self.published_signal='.html'
        self.cover_xpath = './/input[contains(@id,"cover")]/..//input[contains(@accept,"jpg")]'
        #self.brand_path = r'C:\Users\Administrator\Desktop\test\公众号\报告\info\brand-pcauto.json'
        self.brand_path = os.path.join(current_path,'报告','info','brand-pcauto.json')
        self.make_sure_cover = True#如果封面上传长时间加载会设置为False，并在publish再次尝试

    def login(self,use=None,code=None):
        if use==None:
            use = self.use
        if code==None:
            code = self.code

    def paste(self,part):
        if part == 'title':
            self._paste_title()

        elif part == 'body':
            self.scroll_to_top()
            
            self.switch_to_frame(locator=self.locator)
            body_locator = (By.XPATH,self.body)
            self.ctrl_v(body_locator,self.intro)
            self.driver.switch_to.parent_frame()
        else:
            print('请输入"title"或者"body"。\n')

    def _modify_bold_and_heading(self):#
        "需不需要对加粗和标题中的&nbsp;进行修改还要看来源"
        "如果一直在编辑框内传递，&nbsp;原封不动保存"
        pass

    def modify_content(self):
        '与车家号相似'
        locator = (By.XPATH,'.//iframe[contains(@class,"edit")]')
        self.switch_to_frame(locator=locator)
        body = self.find(self.body)
        html = self._get_tag_html(body)

        # bold_text = self.message['bold']
        # for i in bold_text:
        #     target = r'<%s>%s(<br>)?</%s>' %(self.paras_tag,self.escape_word(i),self.paras_tag)
        #     repl = '<%s><%s>%s</%s></%s>'  %(self.paras_tag,self.bold,i,self.bold,self.paras_tag)
        #     res = re.subn(target,repl,html)
        #     self._modify_warning(res[1],i)
        #     html = res[0]

        for i in self.message['bold']+self.message['strong']:
            target = r'<%s(?P<id>[^>]*?)>%s(\s)?(<br>)*?</%s>' %(self.paras_tag,self.escape_word(i),self.paras_tag)
            #target = r'<%s[^>]*>%s(<br>)?</%s>' %(self.paras_tag,self.escape_word(i),self.paras_tag)
            #repl = '<%s>%s</%s>'  %(self.bold,i,self.bold)
            repl = r'<%s\g<id>><%s>%s</%s></%s>'  %(self.paras_tag,self.bold,i,self.bold,self.paras_tag)
            res = re.subn(target,repl,html)
            self._modify_warning(res[1],i)
            html = res[0]
        style_pattern = r'<%s(?P<id>[^>]*?)>.*?</%s>' %(self.paras_tag,self.paras_tag)
        paras_style = re.search(style_pattern,html).group('id')

        for i in self.message['heading']:

            target = r'>%s(<br>)?<' %self.escape_word(i)
            repl = '><%s%s><%s>%s</%s><%s><'  %(self.paras_tag,paras_style,self.heading, i, self.heading,self.paras_tag)
            res = re.subn(target,repl,html)
            self._modify_warning(res[1],i)
            html = res[0]

        html = self._bold_names(html)
        
        self._change_html(body,html)

        self.driver.switch_to.parent_frame()

    def _change_cover_size(self,target_size =  (1280,853),img_format='jpg'):
        img  = CompressImage(self.message['cover_path'])
        if img.size[0] < target_size[0] or img.size[1] < target_size[1]:
            return img.extendMargin(target_size,'pcauto','white',img_format=img_format)
        else:
            return self.message['cover_path']
    
    def click_loaded_cover(self):
        "为加载时间容易过长设计"
        try:
            sure = self._wait_for_displayed(10,(By.XPATH,'.//div[@class="cropBtn"]//*[contains(@id,"Yes")]'))
            time.sleep(0.2)
            self._js_click(sure)
        except TimeoutException:
            self.make_sure_cover = False
            print('%s上传图片可能过大，请稍后再尝试\n' %self.source)

    def check_box(self,again=False):

        #设置标签
        cover_path = self._change_cover_size()#使封面大小不小于900×600
        tags_ele = self.find('.//div[@class="tags"]')
        tags_name = ['行业分析','新车资讯','汽车科技']#貌似只能选三个
        for i in tags_name:
            try:
                tag = tags_ele.find_element_by_xpath('.//a[text()="%s"]' %i)
                time.sleep(0.5)
                self._js_click(tag)
            except TimeoutException:
                print('%s在添加标签%s是出现超时\n' %(self.source, i))


        #设置品牌
        brands = json.loads(open(self.brand_path).read())
        for i in brands:
            if i in self.message['tags']:
                self._wait_for_clickable(2,(By.XPATH,'.//div[contains(@id,"brand")]//div[@class="arr"]')).click()
                self.find('.//div[@class="opt"]//a[contains(text(),"%s")]' %i).click()
                break


        #封面设置
        self.scroll_to_bottom()
        
        cover_set = self._wait_for(3,(By.XPATH,self.cover_xpath))
        self._load_cover(cover_set,again=again,img_path=cover_path)

        self.click_loaded_cover()#加载时间容易过长

    def publish(self):
        if not self.make_sure_cover:
            self.click_loaded_cover()

        submit = self.find('.//div[contains(@class,"submit")]/a[contains(@class,"submit")]')
        self._js_click(submit)
    
    def generate_branch_file(self):
        dir_path=self.brand_path
        self._wait_for_clickable(2,(By.XPATH,'.//div[contains(@id,"brand")]//div[@class="arr"]')).click()
        brand_list_ele = self.finds('.//div[@class="opt"]//a')
        brands = []

        for i in brand_list_ele:
            brands.append(i.text)#自动省略首位空格

        if dir_path:
            if not os.path.exists(dir_path):
                print('由于所输入的路径不存在，正在生成一个该路径。\n')
                os.mkdir(dir_path)
                path = os.path.join(dir_path,'branch.json')
                finall_path = path
            
                
        else:
            path=self.brand_path
            finall_path = os.path.join(os.getcwd(),path)
        with open(path,'w') as f:
            f.write(json.dumps(brands))
        
        print('文件保存在:\n%s' %finall_path)
    
    def _status(self,element):
        status = element.find_element_by_xpath('.//div[contains(@class,"condition")]')
        return status.text

    #存在搜索框
    def collect_info(self,title,next_page=False,read_count=False):
        essay_list = self._wait_for_all(4,(By.XPATH,'.//div[@class="lists-detail"]//li'))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath('.//a[@class="art-tit"]')
            full_title = title_and_url.text
            #print(full_title)
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                
                res['read_counts'] = -1

                # if read_count:
                #     res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res

        else:
            if next_page and essay_list:

                sbox = self._wait_for_clickable(3,(By.XPATH,'.//*[contains(@class,"search")]//input'))
                self.text_box(sbox,title)
                button = self.find('.//*[contains(@class,"search")]//input[@name="Submit"]')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=next_page,read_count=read_count)
                
                else:
                    print('%s切换到下一页后，页面载入时间过长' % self.source)
                    return {}

            print('没有在%s中搜到所要的文章。\n' %self.source)
            return {}
            

######################车市号##############################
class Cheshi(Web):

    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'strong'
        self.heading = 'strong'
        self.charct = 'p'
        self.body = './/body'
        self.title_locator =  (By.XPATH,'.//input[@placeholder and contains(@id,"title")]')
        self.published_signal='.html'

    def paste(self,title):
        pass

    def check_box(self):
        pass
    
    def _status(self,element):
        return element.find_element_by_xpath('.//div[@class="state"]').text
    
    def _get_readcount(self,element):
        str_count = element.find_element_by_xpath('.//span/i[contains(@class,"browse")]/..').text
        return int(str_count)

    #存在搜索框，但暂时用翻页继续查找文章，翻页上限5次
    def collect_info(self,title,next_page=False,read_count=False,times=5):
        essay_list = self._wait_for_all(4,(By.XPATH,'.//div[@class="my_news_list"]/div'))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath('.//a[contains(@href,"news/") and contains(@class,"h")]')
            full_title = title_and_url.text
            #print(full_title)
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                
                res['read_counts'] = self._get_readcount(i)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res

        else:#暂无
            if next_page and times:
                times-=1
                self.scroll_to_bottom()
                button = self.find('.//li[@class="next"]/a')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=next_page,read_count=read_count,times=times)
                
                else:
                    print('%s切换到下一页后，页面载入时间过长' % self.source)
                    return {}

            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}


class Yiche(Web):
    def __init__(self,driver,source,message,use,code,current_path='',add_intro=False):
        Web.__init__(self,driver,source,message,use,code,current_path=current_path,add_intro=add_intro)
        self.bold = 'strong'
        self.heading = 'strong'
        self.paras_tag = 'p'
        self.body = './/div[contains(@class,"editor")and @contenteditable]'
        self.title_locator = (By.XPATH,'.//div[@class="article-title"]//input[@type="text" and contains(@placeholder,"标题")]')
        self.cover_xpath ='.//div[@class="article-cover"]//input[@type="file"]'
        
        self.published_signal='contentManage'
    
    # def paste(self):
    #     pass

    def check_box(self):
        self.scroll_to_bottom
        img  = self.find(self.cover_xpath)
        img.send_keys(self.message['cover_path'])

    def publish(self):
        button = self.find('.//div[@class="article-footer-box"]//span[text()="发布"]/..')
        self._js_click(button)

    def _status(self,element):
        try:
            element.find_element_by_xpath('.//div[contains(@class,"published")]')
            return '已发布'
        except NoSuchElementException:
            return '未发布'

    def _get_readcount(self,element):
        return int(element.find_element_by_xpath('.//span[@class="read"]').text)

    #存在搜索框，但暂时用翻页继续查找文章，翻页上限5次
    def collect_info(self,title,next_page=False,times=5,read_count=False):
        essay_list = self._wait_for_all(4,(By.XPATH,'.//ul[@class="image-list"]/li'))
        res = {}
        for i in essay_list:
            title_and_url = i.find_element_by_xpath('.//h5[@class="title"]/a')
            full_title = title_and_url.text
            #print(full_title)
            if title in full_title:
                status = self._status(i)
                res['status'] = status
                if status != '已发布':
                    print('%s号的文章 %s 状态是 %s ,可能还没有过审。\n' %(self.source,full_title,status))
                    return res
                
                res['url'] = title_and_url.get_attribute('href')
                res['title'] = full_title
                
                res['read_counts'] = self._get_readcount(i)

                if read_count:
                    res['screen_shot_path'] = self.screen_shot_for_element(i)

                return res

        else:#暂无
            if next_page and times:
                times-=1
                self.scroll_to_bottom()
                button = self.find('.//li[@class="next"]/a')
                self._js_click(button)

                if self.page_switch_test():

                    return self.collect_info(title,next_page=next_page,read_count=read_count,times=times)
                
                else:
                    print('%s切换到下一页后，页面载入时间过长' % self.source)
                    return {}

            else:
                print('没有在%s中搜到所要的文章。\n' %self.source)
                return {}   


##废弃##
def refresh_cookie_1(self):
    cookies=self.driver.get_cookies()#获取当前窗口的cookie
    new = []
    for i in cookies:
        j = dict()
        try:
            if i['domain'].find('.') == 0:
                j['domain'] = i['domain']
                j['name'] = i['name']
                j['value'] = i['value']
                j['path'] = '/'
                j['expires'] = None
                new.append(j)
        except KeyError:
            continue
    for i in new:
        if i['domain'].find('.') == 0:
            domain  = i['domain']
            break
    else:
        print("没有以'.'开头的域名。\n")

    end = domain.find('.com')
    if end==-1:
        end = domain.find('.net')
        if end == -1:
            print('没有找到域名中的特征字段。\n')
    start = domain.rfind('.',0,end) + 1
    name = domain[start:end]
    cookie_list_path = r'C:\Users\Administrator\Desktop\python\习题\项目\cookies\test_1'
    cookie_path  = os.path.join(cookie_list_path,'%s.json' %name)
    if os.path.exists(cookie_path):
        Winhand().sonic_warn()
        ans = input('该cookie会被覆盖，请确定名称是否正确。\n(确认按回车，取消按字母再键回车)\n')
        if ans:
            return None

    with open(os.path.join(cookie_list_path,'%s.json' %name),'w') as f:
        f.write(json.dumps(new))
        return True

def refresh_cookie_2(self):#所有域名的都保
    cookies=self.driver.get_cookies()#获取当前窗口的cookie
    new = []
    for i in cookies:
        j = dict()
        try:
            if i['domain']:
                j['domain'] = i['domain']
                j['name'] = i['name']
                j['value'] = i['value']
                j['path'] = '/'
                j['expires'] = None
                new.append(j)
        except KeyError:
            continue
    for i in new:
        if i['domain'].find('.') == 0:
            domain  = i['domain']
            break
    else:
        print("没有以'.'开头的域名。\n")

    end = domain.find('.com')
    if end==-1:
        end = domain.find('.net')
        if end == -1:
            print('没有找到域名中的特征字段。\n')
    start = domain.rfind('.',0,end) + 1
    name = domain[start:end]

    cookie_list_path = r'C:\Users\Administrator\Desktop\python\习题\项目\cookies\test_2'
    cookie_path  = os.path.join(cookie_list_path,'%s.json' %name)
    if os.path.exists(cookie_path):
        Winhand().sonic_warn()
        ans = input('该cookie会被覆盖，请确定名称是否正确。\n(确认按回车，取消按字母再键回车)\n')
        if ans:
            return None

    with open(os.path.join(cookie_list_path,'%s.json' %name),'w') as f:
                f.write(json.dumps(new))
                return True
##废弃##