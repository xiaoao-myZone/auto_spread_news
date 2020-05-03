import json,time,os,re,io
import requests,bs4
import sys
#sys.path.append(r'C:\Users\Administrator\Desktop\python\习题\项目\publish_news')
from cookie_login import Cookie_login
from web_class import *
from account import get_acount_date
    
datas = get_acount_date()

log_url = datas.loc['log']

publish_url = datas.loc['publish']

query_url = datas.loc['query']


C = Cookie_login()
d = C.driver


W = Web(d,'test',C.message,'','')






