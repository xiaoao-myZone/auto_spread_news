from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException,TimeoutException,\
    StaleElementReferenceException,NoSuchWindowException,WebDriverException,UnexpectedAlertPresentException
from selenium.webdriver.common.action_chains import ActionChains
import json,time,os,re,traceback,io,copy,sys
import requests,bs4
from timetransfer import timetransfer
from PIL import Image
from relay import map_name_class
from easyExcel import EasyExcel
from winhand import Winhand
#from mysql import MySql
from compress_img import CompressImage
from functools import wraps
from account import get_acount_date

current_path = os.path.abspath(__file__)
current_path = os.path.split(current_path)[0]
ini_path = os.path.join(current_path,'ini.txt')
current_path = os.path.split(current_path)[0]
current_path = os.path.join(current_path,'公众号')


with open(ini_path) as file:#gbk编码
    chrome_setting_path = file.readline()[0:-1]#去掉结尾的\n
    chromedriver_path = file.readline()[0:-1]#去掉结尾的\n

datas = get_acount_date()

log_url = datas.loc['log']

publish_url = datas.loc['publish']

query_url = datas.loc['query']

web_names = datas.loc['name']

#添加新平台需要修改的地方，需要在报告excel中添加对应新平台
map_zh_eng = {
    '百家号':'baidu',
    '网易号':'163',
    '新浪微博':'weibo',
    '新浪看点':'sina',
    '大风号':'ifeng',
    '大鱼号':'dayu',
    '趣头条':'qutoutiao',
    '搜狐号':'sohu',
    '有车号':'youcheyihou',
    '车友号':'maiche',
    '微信号':'weixin',
    '一点号':'yidianzixun',
    '头条号':'toutiao',
    '车家号': 'autohome',
    '企鹅号': 'qq',
    '知乎号': 'zhihu',
    '太平洋号':'pcauto',
    '车市号':'cheshi',
    '易车号':'yiche',

}
#增减平台从这里操作
publish_list = (
    'sohu',

    'autohome',#尽量靠前
    'toutiao',
    'baidu',
    'sina',
    
    '163',
    'yidianzixun',
    #############以上为主要平台################
    'dayu',
    'ifeng',
    'youcheyihou',
    'qutoutiao',
    
    'maiche',
    'zhihu',
    'pcauto',
    'yiche',

    'weibo',

    )

collect_list = (

    'sohu',
    'autohome',
    'toutiao',
    'baidu',
    'sina',
    '163',
    'yidianzixun',

    'dayu',
    'ifeng',
    'youcheyihou',
    'qutoutiao',
    'weibo',
    
    
    'maiche',
    'zhihu',
    'qq',
    'pcauto',
    'cheshi',
    'yiche',
    )

#增减微信同步文章
syn_list = ['youcheyihou','qq']

#可以添加腾讯视频链接的平台
video_able = ['sohu','','','']

main_webs = ['sohu','toutiao','sina','yidianzixun','baidu']
zero_width_sign = [
    
        r'\t',r'\n',r'\v',r'\f',r'\r',r'\u00a0',r'\u2000',r'\u2001',
        r'\u2002',r'\u2003',r'\u2004',r'\u2005',r'\u2006',
        r'\u2007',r'\u2008',r'\u2009',r'\u200a',r'\u200b',r'\u2028',r'\u2029',r'\u3000',
    ]

class Cookie_login():
    
    def __init__(self,driver=None,noImage=False,ant_crl=False,save_path=current_path):
        chrome_options = Options()
        chrome_options.add_argument(r"user-data-dir=%s" %chrome_setting_path)

        prefs = {'profile.default_content_setting_values' :{'notifications' : 2}}#关闭chrome系统弹窗，不过貌似不怎么有效
        if noImage:
            prefs['profile.managed_default_content_settings.images'] = 2
        else:
            prefs['profile.managed_default_content_settings.images'] = 1
        chrome_options.add_experimental_option('prefs',prefs)
        if ant_crl:
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])#反知乎反爬虫
        #chrome_options.add_argument("window-size=1024,768")
        if not driver:
            self.driver = webdriver.Chrome(options=chrome_options, executable_path=chromedriver_path)
        else:
            self.driver = driver
        #设置访问超时
        self.driver.set_page_load_timeout(12)
        #self.driver.delete_all_cookies()
        #print(self.driver.get_cookies())
        self.message = dict()
        #self.driver.maximize_window()
        self.webs = {}
        self.handle_dict = {}
        self.main_handle = ''
        self.collect_message={}

        self.default_author = '葛帮宁'#默认作者
        self.cover_url = ''
        self.tencent_body = './/div[@class="melo-container-page"]'#目前是直接跳过这一步寻找paras
        self.tencent_paras = './/div[contains(@class,"paragraph") and @style]'
        self._wechat_body = './/div[@id="js_content"]'
        self.title_pattern = r'(（|\()?标题(）|\)|\s*(:|：)?)\s*'
        self.intro_pattern = r'(（|\()?导语(）|\)|\s*(:|：)?)\s*'
        #路径
        self.main_path = save_path
        self.cover_path = os.path.join(self.main_path,'图片')
        #self.cover_path = r'C:\Users\Administrator\Desktop\test\公众号\图片'
        self.info_path = os.path.join(self.main_path,'报告','info')
        #self.info_path = r'C:\Users\Administrator\Desktop\test\公众号\报告\info'
        self.report_save_path = os.path.join(self.main_path,'报告')
        #self.report_save_path = r'C:\Users\Administrator\Desktop\test\公众号\报告'
        self.report_template_path = os.path.join(self.info_path,'统一模版.xlsx')
        self.message_cache_path =   os.path.join(self.info_path,'message.json')#用来缓存上一次分析的文章的信息
        self.collect_info     =     os.path.join(self.info_path,'collect_info.json')#用来缓存上次收集到的链接信息
        self.msg_path       =       os.path.join(self.info_path,'msgid.json')
        self.content_for_tag_path = os.path.join(self.info_path,'content.txt')
        self.branch_path       =    os.path.join(self.info_path,'branch.json')
        #路径

############################ tools ######################################################### 
#tools

    def _js_click(self,element):
        self.driver.execute_script("arguments[0].click()",element)

    def switch_to_frame(self):
        frame = self._wait_for(4,(By.XPATH,'.//iframe'))
        self.driver.switch_to.frame(frame)

    def login_by_hand(self,logurl,web_name,ready=False):#
        if not ready:
            self._get_url(logurl)
        else:
            while True:
                Winhand().sonic_warn()
                command = input("Please login by hand,\nand if you loggedin,tap Enter.")
                if command == 'q' or command == 'Q':
                    break
                #if self.get_cookies(web_name):#get_cookies函数：如果cookie不为空返回True，并且保存
                return 
                
    def is_login(self):
        self.driver.implicitly_wait(10)
        try:
            self._wait_for(2,(By.XPATH,'//*[contains(text(),"帮宁工作室")]'))
        except Exception:
            return False
        return True

    def get_uniform_name(self,title):#只适用于首页
        if '百家号' in title:
            return 'baidu' 
        elif '微博' in title:
            return 'weibo'
        elif '新浪' in title:
            return 'sina'
        elif '搜狐' in title:
            return 'sohu'
        elif '网易' in title:
            return '163'
        elif '大鱼' in title:
            return 'dayu'
        elif '大风' in title:
            return 'ifeng'
        elif '有车' in title:
            return 'youcheyihou'
        elif '趣头条' in title:
            return 'qutoutiao'
        elif '头条号' in title:
            return 'toutiao'
        elif '一点号' in title:
            return 'yidianzixun'
        elif '车友头条' in title:
            return 'maiche'
        elif '车家号' in title:
            return 'autohome'
        else:
            print('网站 %s 没有对应的统一命名。\n' %title)
            return None
        
    def get_handle_dict(self):
        handle_dict = dict()
        for i in self.driver.window_handles:
            self.driver.switch_to.window(i)
            domain = self.driver.current_url
            unifo_name = self.get_keyword_from_domain(domain)
            if not unifo_name:
                print(' %s 的域名中没有关键字。\n' %self.driver.title)
            if unifo_name:
                handle_dict[unifo_name] = i
        return handle_dict
    
    def refresh_handle_dict(self):
        self.handle_dict = self.get_handle_dict()
        try:
            str(self.message['source'])
        except KeyError:
            ans = int(input('请输入文章来源(输入1表示微信，输入2表示腾讯文档):\n'))
            if ans==1:
                self.message['source']='weixin'
            elif ans==2:
                self.message['source']='tencent'
            else:
                print('输入错误')
        try:
            self.switch(self.handle_dict['qq'])
            url = self.driver.current_url
            if self.message['source']=='weixin':
                char = '//mp.weixin.qq.com/'
            elif self.message['source']=='tencent':
                char = '//docs.qq.com/'
            else:
                print('文章来源不明。\n')
                return 
            if char in url:
                self.main_handle= self.handle_dict['qq']
            if self.message['model']!='collect':
                del self.handle_dict['qq']
        except KeyError:
            pass
    
    def get_keyword_from_domain(self,domain):
        end = domain.find('.com')
        if end==-1:
            end = domain.find('.net')
            if end == -1:
                print('域名分析中中没有关键字。\n')
                return False
        start = domain.rfind('.',0,end)
        if start<0:
            start = domain.rfind('/',0,end)
        start += 1
        name = domain[start:end]
        return name

    def maxmizeWindow(self):
        try:
            self.driver.maximize_window()
        except WebDriverException:
            pass

    def scroll_to(self,y):
        "按照绝对坐标移动，以窗口顶部到达目标值为止，不过这要求y的值小于网页长度减去界面高度的值"
        js="var q=document.documentElement.scrollTop={}".format(y)
        self.driver.execute_script(js)

    def find(self, locator, method=By.XPATH):
        return self.driver.find_element(method,locator)

    def finds(self, locator, method=By.XPATH):
        return self.driver.find_elements(method,locator)

    def search_handle_by_title(self,title,switch=True):
        current = self.driver.current_window_handle
        for i in self.driver.window_handles:
            self.driver.switch_to.window(i)
            if title == self.driver.title:
                if not switch:
                    self.driver.switch_to.window(current)
                return i
        
    def get_new_handle(self,current_handles=None):
        if current_handles==None:
            return self.driver.window_handles[-1]
        else:
            new_handles = self.driver.window_handles
            res = list(set(new_handles) - set(current_handles))[0]
            return res
    
    def switch(self,num):
        if isinstance(num,str):
            if num[:8]=='CDwindow':
                self.driver.switch_to.window(num)
            else:
                try:
                    self.driver.switch_to.window(self.handle_dict[num])
                except KeyError:
                    print('无法识别所要转到的标签页。\n')
                    raise Exception
        elif isinstance(num,int):
	        self.driver.switch_to.window(self.driver.window_handles[num])
        else:
            print('只能输入句柄字符串与整型')
            return False

        return True

    def get_to_bottom(self,content_loactor):#切到发布界面
        #self._wait_for(3,(By.XPATH,'//div[@id="container"]/p'))
        paras = self.driver.find_elements(content_loactor[0],content_loactor[1])
        end = paras[-1]
        ActionChains(self.driver).move_to_element(end).click(end).\
            key_down(Keys.PAGE_DOWN).key_up(Keys.PAGE_DOWN).key_down(Keys.ENTER).\
            key_up(Keys.ENTER).perform()
         
    def open_new_window(self,url,current_handles=None,quick_model=False):#在非快速模式下，打开新窗口并转入
        "均返回新打开的窗口的handle"

        if quick_model:
            js = 'window.open("%s")' %url
            current_handles = self.driver.window_handles
            self.driver.execute_script(js)
            return self.get_new_handle(current_handles)

        else:
            js = 'window.open("")'
            self.driver.execute_script(js)#
            current_handle = self.get_new_handle(current_handles)
            self.driver.switch_to.window(current_handle)
            self._get_url(url)#只有当driver.get(url)得到服务器响应了，该新建窗口的id才会被加入windows_handles中
            return current_handle

    def _get_url(self,url,times=4):
        
        if not url:
            return
        self.driver.set_page_load_timeout(10)
        count = 0
        while True:
            if count<times:
                count+=1
            else:
                print('网址:%s \n第%d次加载失败。\n' %(url,count))
                return False
            try:
                if count!=1:
                    print('网址:%s \n正在执行第%d次加载。\n' %(url,count))
                current_url = self.driver.current_url
                if current_url==url:
                    self.driver.refresh()
                    return True
                else:
                    self.driver.get(url)
                    return True
            except TimeoutException:
                
                time.sleep(10)
                continue

       
    def delete_info(self,web_element):
        web_element.send_keys(Keys.CONTROL+'a')
        web_element.send_keys(Keys.DELETE)

    def scroll_to_bottom(self):
        js="var q=document.documentElement.scrollTop=100000"
        self.driver.execute_script(js)
    
    def scroll_to_top(self):
        js="var q=document.documentElement.scrollTop=0"
        self.driver.execute_script(js)

    def ctrl_v(self,body_locator,introduce=None):#点击-清空-复制
        body = self._wait_for(2,body_locator)
        self.compulsive_click(body)
        if introduce == None:
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)\
                .key_down(Keys.BACKSPACE).key_up(Keys.BACKSPACE).pause(0.3).key_down(\
                    Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        else:
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)\
                .key_down(Keys.BACKSPACE).key_up(Keys.BACKSPACE).pause(0.3).send_keys(\
                    introduce).key_down(Keys.ENTER).key_up(Keys.ENTER).key_down(\
                        Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()

    def ctrl_c(self,body_locator):#全选复制
        try:
            body = self._wait_for_clickable(2,body_locator)

        except TimeoutException:
            body = self._wait_for(1,body_locator)
        #body.location_once_scrolled_into_view
        self.compulsive_click(body)
        
        #self.focus_on(body)
        time.sleep(0.5)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).\
            key_down(Keys.CONTROL).send_keys('c').key_up(Keys.CONTROL).perform()

    def _wait_for(self,time,locator):
        return WebDriverWait(self.driver,time,0.2).until(EC.presence_of_element_located(locator))

    def _wait_for_all(self,time,locator):
        return WebDriverWait(self.driver,time,0.2).until(EC.presence_of_all_elements_located(locator))
    
    def _wait_for_all_displayed(self,time,locator):
        return WebDriverWait(self.driver,time,0.2).until(EC.visibility_of_all_elements_located(locator))
    
    def _wait_for_displayed(self,time,locator):
        return WebDriverWait(self.driver,time,0.2).until(EC.visibility_of_element_located(locator))
    
    def _wait_for_clickable(self,time,locator):
        return WebDriverWait(self.driver,time,0.2).until(EC.element_to_be_clickable(locator))

    def compulsive_click(self,web_element):
        for i in range(10):
            try:
                try:
                    ActionChains(self.driver).move_to_element(\
                        web_element).click(web_element).perform()
                    break
                except Exception:
                    web_element.click()
                    break
            except Exception:
                time.sleep(0.2)
            int(i)

    def dict_attr(self,text):#获取web_elemennt的style，并转化成字典
        mass = text.split()
        keys = []
        values = []
        length = len(mass)
        if length%2 != 0:
            print('The attribute text is not complete.')
            return 
        for i in range(0,length,2):
            keys.append(mass[i][:-1])
            values.append(mass[i+1][:-1])
        return dict(zip(keys,values))

    def print_message(self):
        for i in self.message:
            if i!='html':
                print('%s :%s' %(i,self.message[i]))

    def remove_element_by_js(self,element):
        js = 'arguments[0].parentNode.removeChild(arguments[0])'
        self.driver.execute_script(js,element)

    def _change_html(self,element,content):
        js = 'arguments[0].innerHTML=arguments[1]'
        self.driver.execute_script(js,element,content)

    def tell_out_date(self,name=''):
        fmt = '%Y年%m月%d日 %H:%M'
        t = timetransfer(fmt)
        cookies = self.driver.get_cookies()
        key = 'expiry'
        stamps = []
        for i in cookies:
            if key in i:
                stamps.append(i[key])
        stamps.sort()
        expiry = stamps[0]
        print('%s:' %name)
        print(t.s2f(expiry))

        dst = expiry-time.time()
        if  dst>=0:
            if dst/3600/24 < 2:
                print('%s登录信息还有两天内过期\n' %name)
        else:
            print('%s登录信息已过期\n' %name)
#tools
            
#collect_info

    def file_name(self,title):#获取简化标题
        if '|' in title:
            parts = title.split(' | ')
            if len(parts[0]) > len(parts[1]):
                return parts[0]
            else:
                return parts[1]
        else:
            return title
        # try:
        #     res = re.search(r'.*?(\|)\s?(?P<simple_title>.+)',title).group('simple_title')
        # except AttributeError:
        #     return title
        # #当标题中没有|时，匹配值为空
        # if not res:
        #     res = title
        # return res

    def _make_img_file(self,title):
        path = self.cover_path
        file_path = os.path.join(path,title)
        os.mkdir(file_path)
        return file_path

    def _collect_urls(self,need_list,title,full_message=False):
        urls = {}
        for i in need_list:
            self.driver.switch_to.window(self.handle_dict[i])
            try:
                plt = datas[i]
                message = map_name_class(i)(self.driver,plt['name'],self.message,plt['account'],plt['code'],'').collect_info(title)
            except TimeoutException:
                print('%s搜集信息超时。\n' %datas[i]['name'])
                message={}
            try:
                #print('%s:%s\n' %(message['title'],message['url']))
                urls[i] = (message['title'],message['url'])
            except (KeyError,TypeError):
                urls[i] = ('无','无')
        if full_message:
            return message
        else:
            return urls

    def collect_main_urls(self,titles=(),generate_report=True,again=False):
        
        self.message['source'] = 'weixin'
        message = self.get_message(normal=False)

        if not again:
            try:
                message['source']
            except KeyError:
                message['source'] = 'weixin'
                message['title'] = '这是一个title'

            need_list = ['sina','baidu','sohu','yidianzixun','163','maiche']
            for i in need_list:
                if i not in self.handle_dict:
                    self.handle_dict[i] = self.open_new_window(query_url[i],quick_model=True)
                else:
                    self.switch(i)
                    if self.driver.current_url!=query_url[i]:
                        self._get_url(query_url[i])
                    else:
                        self.driver.refresh()

        if not titles:
            titles = list(titles)
            print('每篇文章的关键字按回车确认，直接按回车结束，按q或者Q重新输入\n')
            if generate_report:
                while True:
                    keyword = input('\n请输入搜索文章关键字:\n')
                    if keyword:
                        if keyword=='q' or keyword=='Q':
                            self.collect_main_urls(titles=(),generate_report=generate_report,again=True)
                        else:
                            titles.append(keyword)
                    else:
                        break
            # else:
            #     num = 1
        
        All = []
        if isinstance(titles,str):
            titles = [titles]
        num = len(titles)
        for i in range(num):
            title = titles[i]
            #title = input('请输入标题关键词：（回车默认收集各个平台第一篇文章，按q退出）\n')

            # if title=='q' or title=='Q':
            #     return
            res  = self._collect_urls(need_list,title)
            All.append(res)
        if generate_report:
            for i in res:
                print('\n——%s——:\n' %datas[i]['name'])
                print('这是今天帮宁工作室的更新，麻烦老师推荐一下。\n')
                for j in All:
                    print('%s\n%s' %(j[i][0],j[i][1]))
        else:
            for i in res:
                print('\n——%s——:\n' %datas[i]['name'])
                for j in All:
                    print('标题:%s\n链接:%s' %(j[i][0],j[i][1]))
    
    def _save_in_excel(self,read_count=False):
        "self.collect_message是一个嵌套字典，外层字典的键是统一的平台名称，值包含各种信息的字典"
        save_path = self.report_template_path
        main_path = self.report_save_path
        if not self.collect_message:
            try:
                self.collect_message=self.message['collect_message']
            except KeyError:
                print('信息汇总中没有链接收集信息。\n')
                return

        web_name_column = 2
        item_start_row = 2
        date_column = 4
        title_column = 5
        url_column = 6
        read_count_column = 7
        sheet = 'Sheet1'
        Excel = EasyExcel(save_path)
        item_row = item_start_row
        
        for i in self.collect_message:
            try:
                title = self.collect_message[i]['title']
                if title:
                    title = self.file_name(title)
                    break
            except Exception:
                print('来自"%s"的错误信息:\n' %datas[i]['name'])
                print(traceback.format_exc())

        date = timetransfer().s2f(time.time(),'%m{m}%d{d}')
        while True:
            web_name = Excel.getCell(sheet,item_row,web_name_column)
            if not web_name:
                break
            try:
                unifor_name = map_zh_eng[web_name]
            except KeyError:
                continue
            try:
                Excel.setCell(sheet,item_row,url_column,self.collect_message[unifor_name]['url'])
                try:
                    Excel.setCell(sheet,item_row,date_column,self.collect_message[i]['date'])
                except Exception:
                    Excel.setCell(sheet,item_row,date_column,date)
                Excel.setCell(sheet,item_row,title_column,self.collect_message[unifor_name]['title'])
                if read_count:
                    read_counts = self.collect_message[unifor_name]['read_counts']
                    if read_counts>30:
                        Excel.setCell(sheet,item_row,read_count_column,read_counts)
            except (KeyError,TypeError):
                pass
            item_row += 1

        
        title = self._delete_illegal_char_in_title(title)
        new_path = os.path.join(main_path,'%s.xlsx' %title)
        Excel.save(new_path)
        print(new_path)
        Excel.close()

    def _delete_illegal_char_in_title(self,title):
        title = re.sub(r'\\','',title)
        title = re.sub(r'/','',title)
        title = re.sub(r'\|','',title)
        return title
    
    def save_last_message_in_excel(self,read_count=False):
        "若要记载阅读量，请把read_count设为True"
        self.message=self.get_collect_info()
        self._save_in_excel(read_count=read_count)

    def open_webs(self,need_list,url_type):#在现有的handle_dict基础上打开webs

        for i in need_list:

            if i not in self.handle_dict:
                self.handle_dict[i] = self.open_new_window(url_type[i],quick_model=True)
                time.sleep(1.5)
            else:
                try:
                    self.switch(i)
                    if self.driver.current_url!=url_type[i]:
                        self._get_url(url_type[i])
                    else:
                        if self.message['model']!='publish':
                            try:
                                self.driver.refresh()
                            except TimeoutException:
                                print('%s刷新超时\n' %web_names[i])

                except NoSuchWindowException:
                    self.handle_dict[i] = self.open_new_window(url_type[i],quick_model=True)
                    time.sleep(1.5)

    def collect_all_urls_and_save(self,title=None,read_count=False,next_page=False,from_weixin=False,ready=False):
        "handle_dict参数为None既打开query也创建字典，query_ready为False（非默认值）会重新加载。"
        print('搜索一周前的文章请用next_page=True。\n')
        print('x-x-'*15)
        self.message['model'] = 'collect'
        self.message['collect_message'] = {}
        source = input('请告知文章来源，如果是来自微信，请输入1；\n如果是来自本地，请输入2：（回车退出）\n')
        if source=='1':
            self.message['source'] = 'weixin'
            need_list = list(collect_list)
        elif source=='2':
            self.message['source'] = 'tencent'
            need_list = list(collect_list)
            if 'qq' in need_list:
                need_list.remove('qq')
        elif not source:
            return 
        else:
            print('输入错误。\n')
            return 

        if title==None:
            title = input('请输入标题关键词：(回车退出)\n')
            if not title:
                return 
        if not read_count:
            ans = input('是否需要保存阅读量？\n默认扩大搜索范围（回车默认不保存，输入任意一个字母表示保存）\n')
            if ans:
                read_count=True
                next_page=True


        self.get_webs()
        if not ready:
            self.open_webs(need_list,query_url)

                

        for i in need_list:
            self.driver.switch_to.window(self.handle_dict[i])
            try:
                res = self.webs[i].collect_info(title,read_count=read_count,next_page=next_page)
            except TimeoutException:
                print('%s搜集信息存在超时。' %datas[i]['name'])
                res = {}
            except Exception:
                print('来自"%s"的错误信息:\n' %datas[i]['name'])
                print(traceback.format_exc())
                res = {}
            self.collect_message[i] = res

        self._save_message()

        self._save_in_excel(read_count=read_count)

    def get_message(self,normal=True):
        path=self.message_cache_path
        res = json.loads(open(path).read())
        res['new'] = False
        try:
            res['source']
        except KeyError:
            ans=input('请输入来源，‘1’表示来微信，‘2’表示来自腾讯。（按任意字母退出）\n')
            if ans=='1':
                res['source']='weixin'
            elif ans=='2':
                res['source']='tencent'
            else:
                print('已退出。\n')
        if normal:
            self.message = res
            if self.message['source'] =='weixin':
                print('正在打开文章链接...\n')
                self._get_url(res['url'])
        else:
            return res

    def refresh_windows(self):
        for i in self.handle_dict:
            self.switch(i)
            self.driver.refresh()

    def _save_message(self,collect_message=None):
        save_path=self.message_cache_path
        if collect_message:
            self.collect_message = collect_message
        
        if self.message['model']=='collect':
            save_path=self.collect_info
            self.message['collect_message']=self.collect_message
            with open(save_path,'w') as f:
                f.write(json.dumps(self.message))
            return
        else:
            with open(save_path,'w') as f:
                f.write(json.dumps(self.message))

            if self.message['source']=='weixin' and self.message['model'] == 'publish' and self.message['new']:
                pass
                # core_message = self._generate_info_for_mysql()
                #self._save_in_mysql(core_message)
                # Ms = MySql()
                # Ms.add('wechat_news',core_message)
                # Ms.close()
                # print('基本信息已保存入数据库。\n')
    
    def _generate_info_for_mysql(self,message=None):
        if not message:
            message = self.message

        core_message={}
        core_message['title'] = message['raw_title']
        for i in ('url','date'):
            core_message[i] = message[i]
        return core_message

    def _save_in_mysql(self,info=None):
        pass

    def _get_message_from_mysql(self,title,full=False):
        pass
        
    def get_collect_info(self):
        path=self.collect_info
        return json.loads(open(path).read())

    #new_essay
    def search_weixin_essay(self):
        "出现迭代错误后，记得把essay_id加1,提供标题，导语，封面绝对路径，文章链接"
        msg_path=self.msg_path
        url = 'https://weixin.sogou.com/'
        self.open_new_window(url)
        self.driver.delete_all_cookies()

        account_name = '帮宁工作室'
        self.driver.find_element_by_xpath('//input[@id="query"]').send_keys(account_name)
        select_account_search = self._wait_for(3,(By.XPATH,'//input[@value="搜公众号"]'))
        self.compulsive_click(select_account_search)

        weixin_account = 'gbngzs'
        target = self._wait_for(3,(By.XPATH,'//label[text()="%s"]/../..//a' %weixin_account))
        self.compulsive_click(target)#会弹出新窗口
        self.driver.close()
        self.driver.switch_to.window(self.get_new_handle())

        if os.path.exists(msg_path):
            essay_id = json.loads(open(msg_path,'r').read())
        else:
            essay_id = int(input('Please input msgid:(like 1000000316)\n'))
            with open(msg_path,'w') as f:
                f.write(json.dumps(essay_id))
        while True:
            try:
                self._wait_for(3,(By.XPATH,'.//div[@id="history"]/div[@class="weui_msg_card"]'))
                essay_list = self.driver.find_elements_by_xpath('.//div[@id="history"]/div[@class="weui_msg_card"]')
                break
            except TimeoutException:
                Winhand().sonic_warn()
                input('可能有验证码。解决后请回车。\n')
                try:
                    self._wait_for(3,(By.XPATH,'.//em[text()="帮宁工作室"]/..')).click()
                    self.search_handle_by_title('帮宁工作室')#搜索并转到并返回结果句柄
                except TimeoutException:
                    pass
        all_msg_id = []
        
        for i in essay_list:
            msgid = i.find_element_by_xpath('.//div[contains(@class,"appmsg")]').get_attribute('msgid')
            all_msg_id.append(int(msgid))
        for i in all_msg_id:
            if i > essay_id:
                print('有新的文章。\n')
                essay_id = i
                break
            else:
                print('没有新的文章。\n')
                return 


        new_essay_list = self.driver.find_elements_by_xpath('.//div[@id="history"]//div[@msgid="%d"]' %essay_id)
        essay_num = 1
        for essay in new_essay_list:
            self.message = {}
            message  = {}
            style = essay.find_element_by_xpath('./span').get_attribute('style')
            cover_url = style[style.find('http'):style.rfind('jpeg') + 4]
            cover = requests.get(cover_url)
            cover.raise_for_status()
            date = time.strftime("%Y-%m-%d",time.localtime())
            cover_path = r'C:\Users\Administrator\Desktop\test\公众号\图片\%s-%d-%d.jpg' %(date,essay_num,essay_id)
            with open(cover_path,'wb') as f:
                f.write(cover.content)
            raw_title = essay.find_element_by_xpath('.//h4').text
            start = raw_title.find('GBN')
            message['title'] = raw_title[start:]
            #message['win_title'] = self.file_name(message['title'])
            message['introduce'] = essay.find_element_by_xpath('.//p').text
            message['window'] = self.driver.current_window_handle
            message['cover_path'] = cover_path
            message['target_url'] = 'https://mp.weixin.qq.com' + essay.find_element_by_xpath('.//h4').get_attribute('hrefs')
            self.message = message

            self._check_img_and_title()
            #标题不符合要即时输入修改，图片不符合要求，会用key——'change_cover'的bool值标记
            if self.message['change_cover']:
                message['imgs_path'] = self._make_img_file(message['win_title'])##
            self._click_into_essay()
            #获取一级标题
            self.message['heading'] = self._get_heading_text()
            #增加作者，复制正文
            self.message['tags'] = self.generate_tags()
            yield self.message
            essay_num += 1
            self.driver.switch_to.window(message['window'])#自动返回所在标签页
        with open(msg_path,'w') as f:
            f.write(json.dumps(essay_id))

    def _click_into_essay(self,platform='weixin'):#返回作者，写入纯文本，并选中全文，ctr_C
        self.open_new_window(self.message['target_url'])
        self.message['platform'] = platform
        if platform == 'weixin':
            author = self._strip_author()
            paras = self.driver.find_elements_by_xpath('//div[@id="js_content"]/p/span')
            #将文章写入txt,以便后来生成tag
            content_path = r'C:\Users\Administrator\Desktop\python\习题\项目\publish_news\content.txt'
            with open(content_path,'w') as f:
                for para in paras:
                    text = para.text
                    if text:
                        f.write(text.encode("gbk", 'ignore').decode("gbk", "ignore"))
                    
            #将每个图片载入完整
            self.message['imgs_num'] = self._get_imgs_num()[0]
            # 可惜这个地址是webp格式的，如果需要下载，还是将其粘贴到其他平台上再保存到本地

            self._select_area()
            if len(author)<11:
                self.message['author']  = author
            else:
                print('作者名字长度超过10个字符。\n')

    def generate_tags(self):
        file_path = self.content_for_tag_path
        content = open(file_path,'rb').read().decode("gbk", "ignore")
        content = re.sub('&nbsp;','',content)
        import jieba.analyse
        tags = jieba.analyse.extract_tags(content,topK=5)
        return tags

    def _delete_num_with_circle(self,title):
        no_use = []
        res = title
        for i in title:
            if '\u2460'<= i <= '\u32bf':
                if i != '、':
                    no_use.append(i)
    
        nums = len(no_use)
        if nums:
            no_use = list(set(no_use))
            for i in no_use:
                res = res.replace(i,'')
            print('#####标题存在%d个带圈数字，已删除。' %nums)
            print('新标题为：%s\n' %res)
        return res

    def _reverse_title(self,title):#标题
        signal = '|'
        if '|' in title:
            parts = title.split(signal)
            if len(parts) != 2:
                Winhand().sonic_warn()
                title = input('标题存在多个“|”，请重新输入(回车退出):\n')
                if not title:
                    return False
                else:
                    self._reverse_title(title)
            front , body = parts
            front = front.strip()
            body = body.strip()
            
            if len(front) > len(body):

                print('已将标题进行翻转\n')
                parts.reverse()
                return ' | '.join((body,front))
            else:
                return title

        else:
            return title

    def _add_forhead(self,title):
        normal_match=['日常','特写','观察','专题','访谈','观点','见识','跨界']#需要在前面加GBN
        special_match = ['设计','联盟','逝者','汽车记忆','戈恩事件','追踪']#不需要加GBN

        title = self._reverse_title(title)
        if 'GBN' not in title and '|' in title:
            fore = title.split('|')[0].strip()
            for i in normal_match:
                if i == fore:
                    title = 'GBN' + title
                    break
            else:
                for i in special_match:
                    if i == fore:
                        return title
                Winhand().sonic_warn()        
                ans = input('是否添加“GBN特写”? (按任意字母确定，回车取消。)\n')
                if ans:
                    title = re.sub(r'\|\s','',title)
                    title = 'GBN特写 | ' + title

            return title
        else:
            return title

    def _get_byte_size(self,title):
        f = io.BytesIO()
        Bytes = f.write(title.encode('gbk','ignore'))
        f.close()
        return Bytes

    def _check_title_len(self):
        num_size = len(self.message['title'])

        byte_size = self._get_byte_size(self.message['title'])//2
        if 10<byte_size and num_size<31:
            print('标题字数符合要求。\n')
        else:
            if byte_size<=10:
                Winhand().sonic_warn()
                new_title = input('标题：%s 的字数不符合要求，少了%d个字请手动输入。\n' %(self.message['title'],11-byte_size))
            else:
                Winhand().sonic_warn()
                new_title = input('标题：%s 的字符数大于30，多了%d个字请手动输入。\n' %(self.message['title'],num_size-30))
            self.message['title'] = new_title
            self._check_title_len()

    def _check_intro_len(self):
        diff = len(self.message['introduce'])-44
        if diff>0:
            print('#####导语过长，需要在微博上修改，需要删掉%d个字\n' %diff)

    def _check_img_and_title(self):
        #11-30字的标题，2比特算一个字符。封面长宽分别要大于560*315，长宽比最好是3:2
        #title_path=r'C:\Users\Administrator\Desktop\python\习题\项目\publish_news\title.txt'
        self.message['raw_title'] = self.message['title'].strip()

        self.message['title'] = self._delete_num_with_circle(self.message['title'])
        self.message['title'] = self._add_forhead(self.message['title'])

        self._check_title_len()
        self._check_intro_len()

        res = self._check_cover_size(self.message['cover_path'])
        self.message['change_cover'] = res
        
    def _check_cover_size(self,img_path):
        bt_size = os.path.getsize(img_path)/1024
        if bt_size>500:
            self.message['cover_path'] = CompressImage(img_path,500).do_it()
            img_path = self.message['cover_path']
            #print('封面大于500Kb。')
        cover = Image.open(img_path)

        ration = cover.size[0]/cover.size[1]
        if ration<1.32:
            print('#####封面宽长比略低，可能在封面剪切时需要手动修改。\n')
            return False
        else:
            return True
        # else:
        #     x_margin = cover.size[0] - 560
        #     y_margin = cover.size[1] - 315
        #     if -71<x_margin<0 or -51<y_margin<0:
        #         self.message['cjh_cover_path'] = CompressImage(img_path,500).extendMargin((560,315),'autohome')
            # else:
            #     print('#####封面大小不满足要求。')
            #     if x_margin<0:
            #         print('宽与标准相差%dpix\n' %x_margin)
            #     else:
            #         print('长与标准相差%dpix。\n' %y_margin)
            #message['change_cover']  = True
            
    def _check_author_is_too_long(self,author):
        if len(author)<11:
            return author
        else:
            Winhand().sonic_warn()
            author = input('作者名字:%s 长度超过10个字符,请修改后输入。\n' %author)
            return author  
    
    def _select_area_1(self,execute=True):
        start = self.driver.find_element_by_xpath('//div[@id="js_content"]/p')
        paras = self.driver.find_elements_by_xpath('.//div[@id="js_content"]/p')
        i=0
        end=None
        while True:
            i-=1
            if '。' in paras[i].text \
                or '？' in paras[i].text \
                or '！' in paras[i].text \
                or '?' in paras[i].text \
                or '!' in paras[i].text \
                or '……' in paras[i].text:
                end = paras[i]
                print('最后一段是:\n%s\n' %paras[i].text)
                #self.message['end_loaction_y'] = end.location['y'] + end.rect['height']
                break
        if execute:
            y_margin = end.rect['height'] + 15
            d = ActionChains(self.driver).move_to_element_with_offset(end,300,y_margin).click_and_hold()
            for para in paras[i:0:-3]:
                d.move_to_element_with_offset(para,300,y_margin).pause(0.3)#往一段的中部向上移动一行
            d.move_to_element_with_offset(start,-21,5).release().\
                key_down(Keys.CONTROL).send_keys('c').key_up(Keys.CONTROL).perform()

    def display_element(self,element):
        self.driver.execute_script ("arguments[0].style=arguments[1]",element,"display: none;")

    def find_intro_element(self,search_range = 10):
        #在前10段非空段落里寻找
        try:
            element_0 = self.find('.//span[text()="%s"]' %self.message['introduce'])
            print('发现文中存在小标题\n')
            for i in range(20):
                element_1 = element_0.find_element_by_xpath('./..')
                if element_1.get_attribute('id')=='js_content':
                    return [element_0]
                else:
                    element_0 = element_1
            
            else:
                print('##定位导语失败，不能删除\n')
            int(i)
        except NoSuchElementException:
            if self.message['introduce']:
                #第二阶段寻找
                paras = self.finds('.//div[@id="js_content"]/*')
                for index,para in enumerate(paras):
                    text = para.text
                    if not search_range:
                        print('##文中没有发现导语\n')
                        
                        return []
                    if text:
                        search_range -= 1
                        if self.message['introduce'] in para.text:
                            print('发现文中存在小标题标题\n')
                            return self.finds('.//div[@id="js_content"]/*[%d]' %(index+1))#需要返回列表

                else:
                    print('##文中没有发现导语\n')
                    int(i)
                    return []
        
    def check_2d_code(self):

        first_img = self.find('.//div[@id="js_content"]//img')
        h = first_img.size['height']
        w = first_img.size['width']
        if h/w>=1.5:
            Winhand().sonic_warn()
            ans = input('第一张图是否存在二维码?(回车确认，输入任意字母表示否)\n')
            if ans == '':
                print('###文章第一张图存在二维码，请在接下来的第三步注意修改\n')
                return True
            else:
                return False
        else:
            return False

    def find_main_tag(self):
        p = self.finds('.//div[@id="js_content"]/p')
        s = self.finds('.//div[@id="js_content"]/section')
        if len(p) > len(s):
            return 'p'
        else:
            return 'section'

    def _contain_end_punctuation(self,text):
        if '。' in text \
            or '？' in text \
            or '！' in text \
            or '?' in text \
            or '!' in text \
            or '……' in text:
            return True
        else:
            return False

    def mask_additional_element(self):
        t = self.find('.//*[@id="img-content"]')
        while t.tag_name !='body':
            bro = t.find_elements_by_xpath('./../*')
            bro.remove(t)
            for i in bro:
                self.driver.execute_script ("arguments[0].style=arguments[1]",i,"display: none;")
            t = t.find_element_by_xpath('./..')
            
    def _select_area(self,execute=True,load=False):#选择复制区域
        if load:
            self._get_imgs_num(load=True)

        main_tag = self.message['main_tag']
        #paras = self.driver.find_elements_by_xpath('.//div[@id="js_content"]//%s' %main_tag)
        paras = self.driver.find_elements_by_xpath('.//div[@id="js_content"]/*')
        i=0
        end = None
        #从js_content的最后一个一级子目录，通过看其中是否有标点，来判断是否是最后一段
        while True:
            i-=1
            text = paras[i].text
            if self._contain_end_punctuation(text):
            # if '。' in text \
            #     or '？' in text \
            #     or '！' in text \
            #     or '?' in text \
            #     or '!' in text \
            #     or '……' in text:
                end = paras[i]
                print('最后一段是:\n%s\n' %end.text)
                end.location_once_scrolled_into_view
                #self.message['end_loaction_y'] = end.location['y'] + end.rect['height']
                break
        j = len(paras)+i#最后一段所在的列表下标
        end_location_y = end.location['y']#最后一段的y坐标
        if execute:
            #img-content包括了正文、大标题、作者、发布日期等
            #这里为了删除头部信息
            head_displayed_paras = self.finds('.//div[@id="img-content"]/*')
            z = 0
            for i in head_displayed_paras:
                if i.get_attribute('id')=='js_content':
                    break
                else:
                    z+=1
                    #self.display_element(i)

            #二维码
            body_displayed_para = self.finds('.//div[@class="qr_code_pc"]')

            
            intro_element = self.find_intro_element()

            #可能有修改项
            try:
                modify_mes = self.find('.//*[@id="js_modify_time"]/..')
                body_displayed_para.append(modify_mes)
            except NoSuchElementException:
                pass
            
            #all_content = self.finds('.//div[@id="js_content"]//%s' %main_tag)
            all_content = self.finds('.//div[@id="js_content"]/*')
            for i in range(len(paras)):
                try:
                    if paras[i+j].location['y'] >= end_location_y:
                        break
                except IndexError:
                    print('#####反选文章内容时，底部界限没有找到。')
                    break
            else:
                print('#####反选文章内容时，底部界限没有找到。')
            
            
            rear_displayed_paras = all_content[i+j+1:]
            if main_tag=='section':
                plus_paras = self.finds('.//div[@id="js_content"]/p')
                for i in plus_paras[::-1]:
                    if i.location['y'] > end_location_y:
                        rear_displayed_paras.append(i)
                    else:
                        break


            all_invisible_list = head_displayed_paras[0:z] + intro_element + body_displayed_para + rear_displayed_paras
            for i in all_invisible_list:
                self.display_element(i)

            self.mask_additional_element()
            make_sure = self.find('.//p[text()="微信扫一扫"]')
            if make_sure.is_displayed():
                print('#####文章二维码部分可能没有删除干净。\n')
            #重新获取正文图片数
            #self.message['imgs_num'] = len(self.finds('.//div[@id="js_content"]//img'))
            body = './/div[@id="js_content"]'
            body = (By.XPATH,'.//div[@id="js_content"]')
            self.ctrl_c(body)

        
    def _get_imgs_num(self,load=False,again=True):
        imgs=[]
        if self.message['source']=='weixin':
            #没加载的图片的class="img_loading"，文章结尾的特征是p[contains(@style,'text-align: center')]
            imgs_1 = self.driver.find_elements_by_xpath('//div[@id="js_content"]/p//img')
            imgs_2 = self.driver.find_elements_by_xpath('//div[@id="js_content"]/section//img')
           
            imgs = imgs_1 + imgs_2
            
            if load:
                self._load_full_page(imgs)
            self.scroll_to_bottom()
            imgs_num = len(imgs)

        elif self.message['source']=='tencent':
            try:
                imgs = self._wait_for_all(10,(By.XPATH,'.//div[@class="melo-container-page"]//img'))
            except TimeoutException:
                if again:
                    
                    return self._get_imgs_num(load=load,again=False)
                else:
                    print('###没有在文章中找到图片\n')
                    return (0,[])

            imgs_num = len(imgs)
            if imgs_num<3 and again:
                Winhand().sonic_warn()
                ans = input('文中图片是否超过2个？回车继续确认，输入字母否定\n')
                if not ans:
                    imgs_num = 3
                else:
                    imgs_num = 1
 
                self._wait_for_all(10,(By.XPATH,'.//div[@class="melo-container-page"]//img'))
            try:
                self.cover_url = imgs[0].get_attribute('src')
            except:
                print('收集封面失败')

                

        return (imgs_num,imgs)

    def _load_full_page(self,imgs):

        for img in imgs:
            img.location_once_scrolled_into_view
            for i in range(20):#不知道为什么等第一张图片载入需要很久，算然第一张图片很早就出现了
                time.sleep(0.2)
                if img.get_attribute('class') != 'img_loading':
                    break
                int(i)
            self.scroll_to_bottom()

    def _is_original(self):
        ans = input('文章是否是原创?(回车表示是，按任意键表示否)\n')
        if ans!='':
            self.message['original'] = False
            
#new_essay         
    
#从腾讯文档中获取新文章信息
    def load_local_essay(self,file_path='',log=True,origin=None):
        "需要电脑上qq处于登陆状态"
        if not file_path:
            file_path = input('请输入word文档关键字再回车\n')
        main_path=self.main_path
        self.message={}
        self.maxmizeWindow()

        if log:
            log_res = self._login_tencent_page()
            if not log_res:
                return 

            elif log_res==1:
                self._login_tencent_page()
            
            elif log_res==2:
                return self.load_local_essay(file_path)

        self._open_upload_window()

        file_path = self._search_load_essay(file_path,main_path)

        Winhand().upload_file(file_path)#使用pywin32导入

        self._wait_for_uploaded()

        #弹出新窗口
        self.driver.close()
        self.switch(-1)
        #检查是否切换到正确的窗口
        file_name = re.search(r'\\{1}(?P<file_name>[^\\]+?).doc+x*',file_path).group('file_name')
        too_long = 0
        try:
            title =  self.driver.title
        except TimeoutException:
            time.sleep(5)
            title =  self.driver.title
            too_long=1
        if file_name in title:
            print('已切换到正确窗口。\n')
            if too_long:
                self.driver.refresh()
        try:
            self._collect_essay_info(origin=origin,refresh_handle=False)
        except Exception:
            self.driver.refresh()
            self._collect_essay_info(origin=origin,refresh_handle=False)
            return
        return
    
    def _login_tencent_page(self):
        "0  退出"
        "1  再次尝试"
        "2  点击了存在的qq账户，但是未能登录成功，重新载入"
        "3  登录成功，并点击展开上传按钮"
        self._get_url('https://docs.qq.com/desktop/?')
        try:
            self.switch_to_frame()
            try:
                #登陆第一个帐号（第一个头像）
                acount = self._wait_for(3,(By.XPATH,'.//div[@class="qlogin_list"]/a'))
                acount.click()
            except TimeoutException:
                try:
                    self.driver.switch_to.parent_frame()
                    new_button  = self._wait_for(5,(By.XPATH,'.//div[@class="new-button-wrap"]/button'))
                    ActionChains(self.driver).pause(0.3).move_to_element(new_button).click().perform()
                    return 3
                except TimeoutException:
                    Winhand().sonic_warn()
                    ans = input('您的qq可能没有登录,请登录后再试。(回车继续，按任意字母退出。)\n')
                    if ans != '':
                        return 0#退出
                    else:
                        return 1#登陆qq继续
            try:
                time.sleep(3)
                new = self._wait_for(5,(By.XPATH,'.//div[@class="new-button-wrap"]/button'))
                ActionChains(self.driver).pause(0.3).move_to_element(new).click().perform()
                return 3
            except TimeoutException:
                Winhand().sonic_warn()
                ans = input('未能登录成功。（回车重新载入，按任意字母退出）\n')
                if ans:
                    return 0
                else:
                    return 2

            time.sleep(0.3)
        except (TimeoutException,NoSuchElementException):
            try:
                time.sleep(2)
                new = self._wait_for(5,(By.XPATH,'.//div[@class="new-button-wrap"]/button'))
                ActionChains(self.driver).pause(0.3).move_to_element(new).click().perform()
                return 3
            except TimeoutException:
                print('切换frame失败，请检查网络再试。\n')
            return 0
    
    def _open_upload_window(self,again=True):
        time.sleep(1)
        start = self._wait_for(5,(By.XPATH,'.//div[@class="new-button-wrap"]/button'))
        ActionChains(self.driver).pause(0.3).move_to_element(start).click().perform()
        try:
            new = self._wait_for_displayed(5,(By.XPATH,'.//*[contains(@class,"new")]//*[contains(text(),"导入")]'))
            ActionChains(self.driver).pause(0.8).move_to_element(new).click().perform()
        except Exception:
            if again:
                self._open_upload_window(again=False)
            else:
                print('出现错误请重试\n')
                raise Exception

    
    def _search_load_essay(self,file_path,main_path):
        if '\\' not in file_path:
            first = []
            for i in os.listdir(self.main_path):
                if file_path in i:
                    first.append(i)
            second = []
            for i in first:
                if '.doc' in i:
                    second.append(i)
            if len(second) < 1:
                Winhand().sonic_warn()
                file_path = input('没有找到文件，请重新输入。(回车退出)\n')
                if file_path:
                    file_path = self._search_load_essay(file_path,main_path)
                else:
                    return
            elif len(second) > 1:
                Winhand().sonic_warn()
                file_path = input('存在多个搜索结果，请重新输入。(回车退出)')
                if file_path:
                    file_path = self._search_load_essay(file_path,main_path=main_path)
                else:
                    return
            else:
                file_path = os.path.join(main_path,second[0])
                print(file_path)
                print('已选中待上传文件。')

        return file_path
    
    def _wait_for_uploaded(self):
        importer = self._wait_for(4,(By.XPATH,'.//div[@class="content-dialog import-file-dialog "]'))
        while True:
            try:
                importer.is_displayed()
                time.sleep(0.5)
            except StaleElementReferenceException:
                print('导入文件成功。\n')
                break
    
    def _get_raw_paras(self):#获取段落的html列表,以&nbsp;</span></div>为标志得到
        
        #间接搜索全文element
        #全文的结构大致为  
        # melo-container-page -*- melo-section -*- melo-text-page -*- mole-paragraph
        #   -*- mole-line -*- melo-line-content -*- <span class="melo-leaf">
        
        content = self.find('.//div[contains(@class,"container") and contains(@style,"opacity")]')
        html = self._get_tag_html(content)
        pattern_1 = r'<div[^>]*>(.+?)&nbsp;</span></div>'
        raw_paras = re.findall(pattern_1,html)
        return raw_paras

    def _get_tencent_txt(self,raw_paras):
        #content_list与raw_paras一一对应
        pattern_2 = r'<span[^>]*>([^<]*)</span>'
        paras_text = []
        
        for i in raw_paras:
            fragments =  re.findall(pattern_2,i)
            s = ''.join(fragments).encode("gbk", 'ignore').decode("gbk", "ignore")#组合并清除零宽字符
            s = re.sub(r'&nbsp;',' ',s)
            paras_text.append(s)#paras_text与raw_paras一一对应
        return paras_text

    def _get_strong_tag_text_for_tencent(self,raw_paras,content_list):
        #文档加粗的特征是@style中含有font-weight: 700，正常的是font-weight: 400
        raw_dialog = [] #为搜索加粗人名做准备
        strong_text = []

        pattern_3 = r'<([^<]*)>[^>]*</span><[^<]*>$'
        for index,i in enumerate(raw_paras):
            style = re.search(pattern_3,i)
            if style:
                if 'font-weight: 700' in style.group(1):
                        strong_text.append(content_list[index])
                else:
                    raw_dialog.append(raw_paras[index])#加粗人名不与加粗段落重复


        pattern_4 = r'<span([^>]*)>([^<]*)</span>'

        names = []
        for i in raw_dialog:
            style_and_text = re.findall(pattern_4,i)
            s = ''
            for j in style_and_text:
                if 'font-weight: 700' in j[0]:
                    s+=j[1]
                else:
                    break#如果开头一段<span>没有加粗则直接跳过这一段
            if s:
                strip_name = re.search(r'([^(:|：)]*)',s)
                if strip_name:
                    names.append(strip_name.group())

        self.message['names'] = self._mono_list(names)
        dealt = set(self.message['bold'] + self.message['heading'] + self.message['extras'])
        strong_text = list(set(strong_text).difference(dealt))
        return strong_text

    def _get_title_for_tencent(self,content_list,search_range = 5):
        "功能:设置message['raw_title'],并返回"
        count = 0

        pattern = re.compile(self.title_pattern)
        for para in content_list:            
            if count==search_range:
                Winhand().sonic_warn()
                ans = input('前%d行没有找到标志性标题，是否以第一行非空为标题（回车确认，按任意键退出）\n' %search_range)
                if ans=='':
                    for para in content_list:
                        if para:
                            raw_title = para.strip()
                            self.message['raw_title'] = raw_title
                            return raw_title
                else:
                    raise Exception
            if not para:
                continue

            title_and_count = pattern.subn('',para,count=1)

            if title_and_count[-1]==0:
                count+=1
                continue
            else:
                self.message['raw_title'] = para
                raw_title = title_and_count[0].strip()
                title = self._add_forhead(self._reverse_title(raw_title))
                return title

    def _get_intro_for_tencent(self,content_list,search_range = 6):
        count = 0

        pattern = re.compile(self.intro_pattern)
        for i,para in enumerate(content_list):            
            if count==search_range:
                print('前%d行没有找到标志性导语\n' %search_range)
                self.message['intro_id'] = -1
                return ''

            if not para:
                continue
            title_and_count = pattern.subn('',para,count=1)
            
            if title_and_count[-1]==0:
                count+=1
                continue
            else:
                self.message['raw_intro'] = para
                self.message['intro_id'] = i
                return title_and_count[0].strip()

    def _get_bold_text_for_tencent(self,paras):#如果作者组有编辑或其他项出现在作者之前，会捕捉不到
        res = []
        
        cons = '来自帮宁工作室（gbngzs）的报道'
        for num,i in enumerate(paras[:10]):
            if cons in i:
                res.append(cons)
                self.message['cons_id'] = num
                break

        else:
            self.message['cons_id'] = -1
            print('####没有找到"%s"这句话\n' %cons)

        intro_id = self.message['intro_id']
        cons_id = self.message['cons_id']
        if intro_id > 0 and cons_id > 0:
            for para in paras[intro_id+1:cons_id]:
                if para:
                    res.append(para)
        else:
            if self.message['author_id']>0:

                res.append(paras[self.message['author_id']])

                if self.message['cons_id']>self.message['author_id']+1:
                    between = self.message['cons_id'] - (self.message['author_id']+1)
                    for i in range(between):
                        txt = paras[self.message['cons_id']+1+i]
                        if txt:
                            res.append(txt)
            bold_fearture  = ['编辑','编译','来源']

            for para in paras[:10]:
                for i in bold_fearture:
                    pattern = r'%s(:|：|/|\|)' %i
                    dst = re.search(pattern,para)
                    if dst:
                        res.append(para)
                        bold_fearture.remove(i)
                        break
                

        
        return res
    
    def _get_author_for_tencent(self,paras):
        author_pattern = r'(作者|记者|文)(\s*?)(:|：|/|\|)(\s*?)(?P<author>[^:：\|]+)'
        for index,i in enumerate(paras[:10]):
            outcome = re.search(author_pattern,i)
            if outcome:
                author = outcome.group('author')
                self.message['author_id'] = index
                return author.strip()#去掉前后的空格
        else:

            print('没有找到作者，使用默认作者:%s\n' %self.default_author)
            self.message['author_id'] = -1
            return self.default_author

    def _get_extra_text(self):#修改完成
        "从腾讯在线文本中可能获得存在连续空格的段落，但是在黏贴到163后，自动将第二个以及后面的空格转化为&nbsp;"
        res = []

        try:
            text = self.message['raw_title']
            if text:
                res.append(text.strip())
        except KeyError:
            print('####没有发现需要除掉的标题。')
            
        try:
            text = self.message['raw_intro']
            if text:
                res.append(text.strip())
        except:
            pass

        return res

    def _detect_table(self):
        try:
            self.find('.//div[@class="melo-section"]//table')
            Winhand().sonic_warn()
            input('####文中存在表格，请截图后原位替换\n')
        except NoSuchElementException:
            return

    def _collect_essay_info(self,origin=None,refresh_handle=True):
        if refresh_handle:
            self.refresh_handle_dict()
            self.switch(self.main_handle)
        Winhand().sonic_warn()
        input('请滑动页面使底部文章载入\n##待全部载入后请滑动至最顶部\n回车继续\n')
        self.message['original'] = True
        self.message['source'] = 'tencent'
        self.message['model'] = 'publish'
        self.message['new'] = True
        self.message['is_main_web'] =  False

        self._wait_for(10,(By.XPATH,'.//div[@class="melo-section"]/div'))

        raw_paras_html = self._get_raw_paras()
        content_list = self._get_tencent_txt(raw_paras_html)
        self.head_search_width = 14
        self.message['title'] = self._get_title_for_tencent(content_list)
        self.message['introduce'] = self._get_intro_for_tencent(content_list)

        self.message['author'] = self._get_author_for_tencent(content_list)
        self.message['bold'] = self._get_bold_text_for_tencent(content_list)
        self.message['heading'] = self._get_heading_text()
        #self.message['name'] = []再上一步中已经定义
        self.message['extras'] = self._get_extra_text()

        self.message['strong'] = self._get_strong_tag_text_for_tencent(raw_paras_html,content_list)
        #检查是否有表格，并处理
        self._detect_table()

        #获取图片数量
        #动态加载，不能全部遍历全文
        self.message['imgs_num'],imgs = self._get_imgs_num()

        self.message['cover_path'] = self._get_cover(imgs)
        self._check_img_and_title()
        self.message['tags'] = self._save_essay_text_and_get_tags(content_list)
        
        
        self._select_area_for_tencent(execute=False)
        #self._get_html()
        self._save_message()
        if origin==None:
            self._is_original()
        self.print_core_message()

    def print_core_message(self):
        print('文章标题为:%s' %self.message['title'])
        print('文章导语为:%s\n' %self.message['introduce'])
        original = '是' if self.message['original'] else '否'
        print('是否原创: %s' %original)

    def _strip_title(self,raw_title):
        try:
            title = re.search(r'GBN.*',raw_title).group()
        except AttributeError:
            title=''
        if not title:
            pattern = re.compile(self.title_pattern)
            title = pattern.sub('',raw_title)
            if title==raw_title:
                return False

        return title.strip()

    def _get_cover(self,imgs,num=0):

        cover_url = self.cover_url
        if cover_url:
            cover_path = self._save_and_get_cover(cover_url)
            return cover_path
        else:
            return ''
    
    def _select_area_for_tencent(self,execute=True):
        self.maxmizeWindow()
        #self._get_imgs_num()
        
        if execute:
            #self.delete_extra_paras()
            body = (By.XPATH,'.//div[@class="melo-section"]/div/div[2]')
            self.ctrl_c(body)
        else:
            return

    def _modify_double_space(self,matched):
        sub = '&nbsp;'
        text = matched.group()
        res=text[0] + sub*(len(text)-1)
        return res

    def _deal_double_space(self,text):
        #res = re.sub(r'\s{2,}',self._modify_double_space,text)
        res = re.sub(r'\s{2,}',' ',text)#对于新的头条号，均转换为一个空格
        return res
        
    def delete_extra_paras(self):
        "使用html删除，页面会被锁死，无法选中，display它们也不行"
        inner_htmls=[]
        for i in range(0,self.message['intro_id']):
            para = self.find('.//div[@class="melo-section"]/div/div[%d]' %(i+1))
            if para.text == self.message['extras'][i]:
                inner_htmls.append(self._get_tag_html(para))

    def _select_para_by_id(self,para_id,step):
        "para_id表示腾讯文档里面ID段落id，step表示在该段落上上下移动的行数，就是把一个str中数字加一个int的操作"
        str_add_int = lambda a,b: str(int(a.group('value')) + b)
        from functools import partial
        move_with_step = partial(str_add_int,b=step)
        res = re.sub(r'(?P<value>\d+)', move_with_step, para_id)
        return res

#从腾讯文档中获取新文章信息    

#直接获取永久链接得到文章信息
    def get_new_essay_by_url(self,url=None,test=False,origin=None):
        self.message={}
        self.message['source'] = 'weixin'
        self.message['model'] = 'publish'
        # try:
            
        #     self.switch(self.main_handle)
        # except:
        #     self.refresh_handle_dict()
        #     try:
        #         self.switch(self.main_handle)
        #     except:
        #         pass
        
        if url:
            self._get_url(url)
        else:
            url = self.driver.current_url
        
        if test:
            self.message['new'] = False
        else:
            self.message['new'] = True
        self.message['is_main_web'] = False
        self.message['url'] = url
        self.message['introduce'] = self._get_intro()
        self.message['title'] = self._get_title()#这是原始标题，在self._check_img_and_title()进行修改
        self.message['author'] = self._strip_author()#在这里设置是否原创
        self.message['imgs_num'] = self._get_imgs_num()[0]-1#减去二维码
        self.message['2Dcode'] = self.check_2d_code()
        self.message['cover_path'] = self._save_and_get_cover()
        self.message['heading'] = self._get_heading_text()
        self.message['bold'] = self._get_bold_text()
        #如果以头条号作为第一个平台，除了qtt和autohome，其他平台均可继承

        self.message['names'] = self._check_dialog()#对话人的名字，需要放在_get_strong_tag_text()之前
        self.message['strong'] = self._get_strong_tag_text()
        
        self.message['tags'] = self._save_essay_text_and_get_tags()
        self.message['date'] = self._get_news_date()
        self.message['extras'] = []
        self.message['main_tag'] = self.find_main_tag()

        #self._add_message_to_attr(message)

        self._check_img_and_title()

        self._select_area(execute=False)

        self._save_message()

        self.print_core_message()

    def _strip_author(self):
        if self.message['source']=='weixin':
            text = self._wait_for(5,(By.XPATH,'//div[@id="meta_content"]')).text
            try:
                author = re.search(r'(原创)(:|：)?\s*(?P<author>.+)(帮宁)+',text).group('author').strip()
                self.message['original'] = True
            except AttributeError:
                text = self.find('.//div[@id="js_content"]').text
                try:
                    author = re.search(r'((作者)|(特约撰稿))\s*\|{1}\s*(?P<author>.+)',text).group('author').strip()
                except AttributeError:
                    print('无法找到作者,用默认作者“葛帮宁”代替\n')
                    author = '葛帮宁'
            self.message['original'] = True

            return self._check_author_is_too_long(author)
        else:
            print('不是来自微信的文章。')

    def _get_intro(self):
        intro = re.search(r'msg_desc\s*=\s*"(?P<intro>.+)"',self.driver.page_source).group('intro')
        return intro

    def _get_title(self):
        title= re.search(r'''msg_title\s*=\s*('|")(?P<title>.+)('|")''',self.driver.page_source).group('title')
        return title

    def _save_and_get_cover(self,cover_url=None):
        main_path=self.cover_path
        if not cover_url:
            cover_url = self.find('.//div[@id="js_content"]//img').get_attribute('data-src')
            #print(cover_url)
            #cover_url = re.search(r'msg_cdn_url+\s*=+\s*"(?P<url>.+)"',self.driver.page_source).group('url')
        cover = requests.get(cover_url)
        cover.raise_for_status()
        file_name = str(int(time.time())) + '.jpg'
        cover_path = os.path.join(main_path,file_name)
  
        with open(cover_path,'wb') as f:
            f.write(cover.content)
        return cover_path

    def _get_cover_for_weixin(self):
        coverPath = re.search(r'msg_cdn_url\s*=\s*"(?P<coverPath>.+)"',self.driver.page_source).group('coverPath')
        return coverPath

    def _save_essay_text_and_get_tags(self,txt_list=None):#生成tags
        "将文章写入txt,以便后来生成tag"
        print('正在生成tags...\n')
        content_path = self.content_for_tag_path
        if txt_list:
            with open(content_path,'w') as f:
                content = ''.join(txt_list)
                try:
                    f.write(content.encode("gbk", 'ignore').decode("gbk", "ignore"))
                except UnicodeEncodeError:
                    print('存在零宽字符，无法生成标签')

        else:
            
            if self.message['source'] == 'weixin':
                pattern = r'>([^<]*?)<'
                content = self.find('//div[@id="js_content"]')
                html = self._get_tag_html(content)
                #paras = self.driver.find_elements_by_xpath('//div[@id="js_content"]//span')
                paras = re.findall(pattern,html)

            elif self.message['source'] == 'tencent':
                paras = []
                paras_tag = self.driver.find_elements_by_xpath(self.tencent_paras)
                for i in paras_tag:
                    paras.append(i.text)

            with open(content_path,'w') as f:
                for text in paras:

                    if text:
                        try:
                            f.write(text.encode("gbk", 'ignore').decode("gbk", "ignore"))
                        except UnicodeEncodeError:
                            for i in zero_width_sign:
                                if i in text:
                                    parts = text.split(i)
                                    text  = ''.join(parts)
                            try:
                                f.write(text.encode("gbk", 'ignore').decode("gbk", "ignore"))
                            except UnicodeEncodeError:
                                print('仍存在编码错误问题')
                                print(traceback.format_exc())

            
        tags = self.generate_tags()
        return tags

    def _get_tag_html(self,element):
        js = 'return arguments[0].innerHTML'
        return self.driver.execute_script(js,element)

    def _insert(self,word,target):
        fragments = word.split(target)
        for i in range(len(fragments)//2):
            fragments[i*2] += '\\'
        return target.join(fragments)

    def escape_word(self,word):
        "将字符变量引用到正则表达式中，如果不进行转义，会出现错误。"
        re_escape = ('\\','^','_','$','|','@','[',']','{','}','(',')')
        for i in re_escape:
            if i in word:
                word = self._insert(word,i)
        return word
    

    def _strip_tags_in_text(self,text):
        text = re.sub(r'<{1}[^>]*?>{1}','',text)
        return text
    
    def _fliter_heading(self,hdlst=None):
        "微信文章中会存在把2019中的20单独放在一个span标签里"
        res=[]
        if hdlst==None:
            hdlst = copy.copy(self.message['heading'])
        for i in hdlst:
            str_num = re.search(r'\d*',i).group()
            num = 0
            if not str_num:
                continue
            for e,j in enumerate(str_num[::-1]):
                num+=pow(10,e) * int(j)
            if num<9:
                res.append(i)
        return res

    def _mono_list(self,list_zh):#list中存在中文时，不能使用list(set())的方法，去除重复元素和空元素
        res = []

        for i in list_zh:
            j = i
            if j and (j not in res):
                res.append(j)
        return res
    
    def _check_dialog(self):
        if self.message['source'] == 'tencent':
        
            content = self.find('.//div[contains(@class,"section")]/..')
            #target = r'<span[^>]*>*?(\:|：)*?</span>'
        else:
            
            content = self.driver.find_element_by_xpath('//div[@id="js_content"]')
            target = r'>([^>]+)</span></strong><[^>]+>(:|：)[^<]+</'
            

        content_html = self._get_tag_html(content)
        res = re.findall(target,content_html)
        if len(res)>1:
            print('#文章中存在对话#\n')
        dialog_names = []
        for i in res:
            j = i[0]
            if j and (j not in dialog_names):
                dialog_names.append(j)
        return dialog_names 

    def _get_heading_text(self):#tencent与weixin通用
        
        if self.message['source'] == 'tencent':
            "腾讯文档的特点是melo-container-page（全文） > melo-section(页) > "
            "melo-melo-text-page > aragraph(段)"
            content = self.find('.//div[contains(@class,"section")]/..')
            target  = r'<span[^>]*>.*?(:|：).*?</span>'

        else:
            "认为字体为font-size: 18px，颜色为rgb(255, 169, 0)的段落为一级标题"
            content = self.driver.find_element_by_xpath('//div[@id="js_content"]')
            #target = r'<span[^>]*>(\d{1,2}(\.|．)?(&nbsp;)*)</span></(p|(section))>'
            target = r'<span[^>]*>(\d{1,2}(\.|．)?(&nbsp;)*)</span>(<span[^>]*></span>)?</(p|(section))>'

        content_html = self._get_tag_html(content)
        res = re.findall(target,content_html)
        target = []
        for i in res:
            j = i[0]
            if j:
                target.append(j)
        res = self._fliter_heading(hdlst=target)
        return res

    def _get_strong_tag_text(self):#tencent与weixin通用
        "存在多个<strong></strong>并列无嵌套 与 <strong><span ...>...</span><span></span></strong>两个模式"
        #微信公众号
        if self.message['source'] == 'weixin':
            content = self.find('//div[@id="js_content"]')
            html = self._get_tag_html(content)
            #target = r'<strong>(.+?)</strong><([^>]+?)>'
            target = r'<strong>(.+?)</strong><((?:(?!strong).)[^>]+?)>'#用来匹配多个strong并列，并且连续
            res_strong = re.findall(target,html)#返回由二元元组组成的列表
            res = []
            #一个strong标签中可能存在并列的strong,首尾的标签会去掉，中间的标签会保留
            
            for i in res_strong:
                if i[1][:4] == 'span':
                    continue#同时如果strong后面接的是span，表示一句话部分加粗，目前来说还是跳过比较好

                if '</span>' in i[0]:
                    part  = ''
                    txt = re.findall(r'>([^<]+)</',i[0])
                    for j in txt:
                        part += j
                    if part:
                        res.append(part)
                #去除<strong>
                else:
                    remove_pattern = r'<(/?)strong>'
                    part = re.sub(remove_pattern,'',i[0])
                    res.append(part)
            for i in res:
                if i in self.message['names']:
                    res.remove(i)
                    
            #检查最后一段括号内的说明是否被加上
            if res:
                last_text = res[-1].strip()
                if (last_text[0] == '（' or last_text[0] == '(') and (last_text[-1] == '）' or last_text[-1] == ')'):
                    del res[-1]
            if res:
                print('存在%d段加粗段落' %len(res))
            return res

    def _get_bold_text(self):
        res = []

        paras_P = self.driver.find_elements_by_xpath('//div[@id="js_content"]/p/span')
                
        paras_S = self.driver.find_elements_by_xpath('//div[@id="js_content"]/section/span')

        paras = paras_P[:10] + paras_S[:10]
        for i in paras:
            if 'rgb(136, 136, 136)' in i.get_attribute('style'):
                j = i.find_element_by_xpath('./..')
                text = self._get_tag_html(j)
                if text:
                    text = self._strip_tags_in_text(text)
                    res.append(text)
        res = list(set(res))

        for i in res:
            if not i:
                res.remove(i)
        return res

    def _add_message_to_attr(self,message):
        for i in message:
            self.message[i] = message[i]

    def _get_news_date(self):
        try:
            date = self.find('.//span[@id="js_modify_time"]').text
        except NoSuchElementException:
            show_date = self._wait_for(3,(By.XPATH,'.//em[@id="publish_time"]'))
            self._js_click(show_date)
            time.sleep(0.5)
            date = self._wait_for(3,(By.XPATH,'.//em[@id="publish_time"]')).text
        return date

#直接获取永久链接得到文章信息

#publish

    def _remove_syn_web(self,need_list):
        for i in syn_list:
            if i in need_list:
                need_list.remove(i)

    def _close_and_delete_extra_webs(self,need_list):
        del_list = []
        for i in self.handle_dict:
            if i not in need_list:
                self.switch(i)
                self.driver.close()
                del_list.append(i)
                #print(i)

        for i in del_list:
            del self.handle_dict[i]

    def get_essay(self,message=None):
        if message:
            if 'http' in message:
                self.get_new_essay_by_url(message)
            else:
                self.load_local_essay(message)
        else:
            if 'http' in self.driver.current_url:
                self.get_new_essay_by_url()
            else:
                ans = input('需要处理本地文稿还是微信页面?\n##本地文稿请按1，微信页面请按2，最后回车。##')
                if ans==1:
                    url = input('请在下行输入微信文章的超链接，再回车:\n')
                    self.get_new_essay_by_url(url)
                elif ans==2:
                    file_name = input('请在下行输入本地文稿的关键字，再回车:\n')
                    self.load_local_essay(file_name)
                else:
                    print('无法识别。')
                    return
    
    def _open_webs_and_check(self,webs_name=None):


        if not webs_name:
            if self.message['model']=='publish':
                if not self.message['is_main_web']:
                    open_list = list(publish_list)
                else:
                    open_list = list(main_webs)
                if self.message['source'] == 'weixin':
                    self._remove_syn_web(open_list)
        else:
            open_list = webs_name


        if not self.handle_dict:
            self.open_webs(open_list,log_url)
        else:
            print('刷新句柄集并关闭无关网页...\n')
            self.refresh_handle_dict()
            self._close_and_delete_extra_webs(open_list)
        
        self.switch(-1)


        self.get_webs()
        

        print("检查登陆情况并转到发布页面。")
        res = self.check_logged()
        if res:
            time.sleep(1)
            ans=''
        else:
            Winhand().sonic_warn()
            ans = input('登陆存在问题，如解决按回车继续黏贴标题，\n按任意一个字母退出。\n')
        if ans:

            return 
        self.refresh_handle_dict()

        self.open_webs(open_list,publish_url)

    def get_webs(self,again=True):

        for i in collect_list:
            plt = datas[i]
            self.webs[i] = map_name_class(i)(self.driver,plt['name'],self.message,plt['account'],plt['code'],current_path)
        


    def check_logged(self,handle_dict=None):
        ready=True
        if not handle_dict:
            handle_dict = self.handle_dict
        
        for i in handle_dict:
            self.switch(handle_dict[i])
            logged = self.webs[i].is_logged()
            if not logged:
                print('%s没有登录。\n' %datas[i]['name'])
                try:
                    self.webs[i].login()
                except Exception:
                    print('%s自动登录出错' %datas[i]['name'])
                ready=False
        return ready  

    def paste_title(self):
        for i in self.handle_dict:
            self.switch(self.handle_dict[i])
            new_handle = self.webs[i].paste('title')
            if new_handle:
                self.handle_dict[i] = new_handle
            time.sleep(0.8)

    def paste_body(self):
        
        body_list  = list(self.handle_dict.keys())
        body_list.remove('163')
        body_list.remove('dayu')
        for i in body_list:
            self.switch(self.handle_dict[i])
            self.webs[i].paste('body')
            time.sleep(0.8)
    
    def modify_content(self):
        for i in self.handle_dict:
            # if i=='dayu':
            #     continue
            self.switch(self.handle_dict[i])
            try:
                self.webs[i].modify_content()
            except Exception:
                print('来自"%s"的错误信息:\n' %datas[i]['name'])
                print(traceback.format_exc())
            time.sleep(1)
            
    def check_box(self):
        handle_dict=copy.copy(self.handle_dict)
        #将知乎自动生成的tag加入到原来的标签中
        sp_web = 'zhihu'
        if sp_web in handle_dict:
            self.switch(handle_dict[sp_web])
            self.webs[sp_web].check_box()
            del handle_dict[sp_web]

        for i in handle_dict:
            self.switch(handle_dict[i])
            try:
                self.webs[i].check_box()
            except Exception:
                print('来自"%s"的错误信息:\n' %datas[i]['name'])
                print(traceback.format_exc())
            time.sleep(1)

    def publish(self):
        handle_dict=copy.copy(self.handle_dict)
        if self.message['source']=='weixin':
            pass
        
        for i in handle_dict:
            self.switch(handle_dict[i])
            try:
                self.webs[i].publish()
            except Exception:
                print('来自"%s"的错误信息:\n' %datas[i]['name'])
                print(traceback.format_exc())
            time.sleep(1.5)
  
    def check_published(self):
        print('正在检查是否正常发布...\n')
        handle_dict=copy.copy(self.handle_dict)
        if self.message['source']=='weixin':
            pass

        for i in handle_dict:
            try:
                self.switch(handle_dict[i])
                if i=='youcheyihou':
                    print('####网站:%s发布失败' %datas[i]['name'])
            except NoSuchWindowException:
                if i=='youcheyihou':
                    continue
                else:
                    print('来自"%s"的错误信息:\n' %datas[i]['name'])

            j = 0
            while True:
                j+=1
                url = self.driver.current_url
                if self.webs[i].check_published(url):
                    break
                elif j<4:
                    time.sleep(1)
                else:
                    print('####网站:%s发布失败' %datas[i]['name'])
                    break
        print('检查完毕\n')
            
    def deal_163(self):
        self.switch(self.handle_dict['163'])
        w_163 = self.webs['163']
        w_163.paste('body')
        time.sleep(1)
        w_163.copy()

    def deal_toutiao(self):
        print('正在处理头条号...\n')
        web = 'toutiao'
        self.switch(self.handle_dict[web])
        tt = self.webs[web]
        tt.paste('body')
        time.sleep(1)
        tt.copy()     

    def deal_youcheyihou(self):
        print('正在处理车友号...\n')
        web = 'youcheyihou'
        self.switch(self.handle_dict[web])
        youche = self.webs[web]
        youche.paste('body')
        time.sleep(1)
        youche.copy()

    def deal_autohome(self):
        print('正在处理车家号...\n')
        web = 'autohome'
        self.switch(self.handle_dict[web])
        autohome = self.webs[web]
        autohome.paste('body')
        time.sleep(1)
        autohome._modify_bold()#根据message修改bold中空格与&nbsp;混杂的情况
        autohome.copy()

    def deal_dayu(self):
        print('正在处理大鱼号...\n')
        self.switch(self.handle_dict['dayu'])
        dayu = self.webs['dayu']
        dayu.paste('body')
        dayu.wait_for_content()
        dayu.modify_content()
        dayu.copy()
        #self.webs['dayu'].copy()
    
    def deal_sohu(self):
        print('正在处理搜狐号...\n')
        web = 'sohu'
        self.switch(self.handle_dict[web])
        sohu = self.webs[web]
        sohu.paste('body')
        time.sleep(1)
        sohu.copy() 

    def step_1(self):
        print("初始化句柄集与webs集")
        self.refresh_handle_dict()
        self._open_webs_and_check()

    def step_2(self):
        self.paste_title()

    def step_3(self,modify=False):
        self.get_webs()
        try:
            #复制文章
            if self.switch(self.main_handle):#switch失败会返回False
                self.refresh_handle_dict()
                if not self.switch(self.main_handle):
                    print('####无法找到文章来源\n')
                    return
            if self.message['source']=='tencent':
                self._select_area_for_tencent()
            elif self.message['source']=='weixin':
                self._select_area(load=True)
            else:
                print('文章来源不明。\n')
                return

            #选择第一篇黏贴的平台
            # first_web = 'toutiao'
            # self.deal_toutiao()
            first_web = 'sohu'
            self.deal_sohu()

            if modify:
                Winhand().sonic_warn()
                input('请手动修改，回车继续\n')
            else:
                time.sleep(1.5)

            for i in publish_list:
                if i not in self.handle_dict:
                    continue
                if i == first_web:
                    continue
                self.switch(i)
                try:
                    self.webs[i].paste('body')
                    time.sleep(0.8)
                except (UnexpectedAlertPresentException,TimeoutException):#针对车家号
                    continue

        except Exception:
                print('来自"%s"的错误信息:\n' %datas[i]['name'])
                print(traceback.format_exc())

    def step_4(self):
        print("修改正文以及设置选项")
        #self.paste_body()
        self.modify_content()
        self.check_box()


    def step_5(self):
        print('发表。')
        self.publish()

    def step_6(self):
        self.check_published()

    def step_p(self):
        self.step_5()
        self.step_6()

    def steps(self,step=False,cbp=False,skip=False,modify=False):
        "step:一步一步执行，默认为否；cbp：发布前暂停检查，默认为否；skip:跳过最开始的询问，默认为否;go_on:在网页都已打开的基础上继续发文章"
        "要想全自动，应该将skip设为True"
        "如果要手动修改头条号的内容，将modify设置为True"
        if self.message['source']=='tencent' and (not self.message['is_main_web']):
            ans = input('是否只发布到主要平台？（直接回车表示确定，输入任意字母再回车表示否定）\n')
            if not ans:
                self.message['is_main_web'] = True

        if (not cbp) and (not skip):
            ans = input('需要在发布前检查吗？(如不需要按回车，如需要，按任意字母后回车\n按s退出)\n')
            if ans:
                if ans=='s' or ans=='S':
                    return
                else:
                    cbp = True

        # self.refresh_handle_dict()
        # print('打开网页中...')
        # self._open_webs_and_check()
        print('开始...\n')

        if step:
            ans = input('输入任意字母退出，回车继续。\n')
            if ans:
                return

        print('正在进行第一步——打开网页...\n')
        self.step_1()
        print('第一步进行完毕。\n')

        if step:
            ans = input('输入任意字母退出，回车继续。\n')
            if ans:
                
                return
        print('正在进行第二步——黏贴标题与导语...\n')
        self.step_2()
        print('第二步进行完毕。\n')

        if step:
            ans = input('输入任意字母退出，回车继续。\n')
            if ans:
                
                return
        print('正在处理第三步——复制粘贴正文...\n')
        self.step_3(modify=modify)
        print('第三步进行完毕。\n')

        if step:
            ans = input('输入任意字母退出，回车继续。\n')
            if ans:
                return

        print('正在处理第四步——修改字体与勾选复选框...\n')
        self.step_4()
        print('第四步进行完毕。\n')

        if step or cbp:
            Winhand.sonic_warn(600)
            ans = input('输入任意字母退出，回车继续。\n')
            if ans:
                return

        print('正在处理第五步——发布...\n')
        self.step_5()

        print('第五步进行完毕。\n')

        print('正在处理第六步——检查发布是否成功...\n')
        self.step_6()
        print('第六步进行完毕。\n')

        print('######本次文章转发结束#######\n')

        self.switch(self.main_handle)

    def delay_publish(self,times=None):
        "请输入小时"
        if not isinstance(times,(int,float)):
            print('输入q退出')
            while True:
                ans = input('请输入推迟发布时间(小时):')
                try:
                    times = float(ans)
                    break
                except Exception:
                    if ans=='q' or ans=='Q':
                        return
                    print('输入错误，请重试')
        seconds = times*3600
        delay_stamp = time.time() + seconds
        fmt = '%Y年%m月%d日 %H:%M'
        t = timetransfer(fmt)
        ans = input('文章将在：%s 发布\n回车确认，输入任意字母退出\n' %(t.s2f(delay_stamp)))
        if ans:
            return
        time.sleep(seconds)
        #print('run')
        self.step_p()

#publish

#test
    def new_web_test(self,name):
        input('测试开始.....(回车继续)')
        self.get_webs()
        web = self.webs[name]
        print('一共有个n阶段进行测试,回车继续,如要退出输入q或者Q，再回车\n')
        ans = input('测试_1:打开主页面...\n')
        if not ans:
            self._get_url(log_url[name])
        else:
            return 

        ans = input('测试_2:打开发布页面...\n')
        if not ans:
            self._get_url(publish_url[name])
        else:
            return 

        ans = input('测试_3:黏贴标题(导语)...\n')
        if not ans:
            web.paste('title')
        else:
            return

        ans = input('测试_4:黏贴正文(请先将正文复制好)...\n')
        if not ans:
            web.paste('body')
        else:
            return

        ans = input('测试_5:修改正文...\n')
        if not ans:
            web.modify_content()
        else:
            return
        
        ans = input('测试_6:勾选文章设置...\n')
        if not ans:
            web.check_box()
        else:
            return

        ans = input('测试_7:发布文章...\n')
        if not ans:
            web.publish()
        else:
            return

        ans = input('测试_8:检查文章是否正常发布...\n')
        if not ans:
            web.check_published()
        else:
            return

        # ans = input('测试_9:检查搜集文章信息...\n')
        # if not ans:
        #     web.collect_info()
        # else:
        #     return
        print('测试结束\n')


        
