from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import json
import time
import os
from selenium.common.exceptions import NoSuchElementException
execute_path = r'C:\Users\Administrator\AppData\Local\Programs\Python\Python37-32\Tools\geckodriver-v0.24.0-win64\geckodriver.exe'
url = 'https://mp.dayu.com/'
driver = webdriver.Firefox(executable_path=execute_path)
print(driver.get_cookies())
driver.get(url)
input()
cookie = driver.get_cookies()
print(cookie)
web_name = 'dayu'
jsonCookies = json.dumps(cookie)
with open(r'cookies\%s.json' % web_name, 'w') as f:
    f.write(jsonCookies)
