#易车号
import requests
from requests import HTTPError
from lxml import etree
url = 'http://mp.yiche.com/manage/contentManage'
headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Cache-Control': 'max-age=0', 
    'Connection': 'keep-alive',
    'Cookie': 'UserGuid=06580630-b680-453e-8bce-dbe18325bb78;\
         CIGDCID=ad312de5bd1a4fe7883d94d492ae6fa0-yiche; csids=3987;\
         .ASPXAUTH=B9CDDE429C5FC62D458D02511343538E84208CE376FF817BFCB2E3A9C256044D0C831FFB9D873FDEEF9A8606037FA02E48979B385436B9BA0C326EDFE652977BBB44C90E36E0D5694021B34DFE9E91773D0BA66427B246014D5A83E0396A77B5592F794BA6A209A041C89F54DEC6B40099E84A757DCD0B44D1BECA31D66867226970E95CAF6A10F5446399B8AF95254A429348CDAEB8E1977D52C4868447D0D28271A948;\
          userid=29483703;\
         username=%e5%b8%ae%e5%ae%81%e5%b7%a5%e4%bd%9c%e5%ae%a4;\
         UserBorsingHistory29483703=1589937701187',
    'Host': 'mp.yiche.com',
    'If-None-Match': '"53313-O4OF0UDdVNTHwSKksHEOwTeli/g"',
    'Upgrade-Insecure-Requests': '1'
}
    
response = requests.get(url=url, headers=headers)
try:
    response.raise_for_status()
    if response.status_code == 200:
        print('请求正常!')
        html_doc = response.content.decode("utf-8")
        tree = etree.HTML(html_doc)
        content_list = tree.findall('.//ul[@class="image-list"]/li')
        for i in content_list:
            title_and_url = i.find('.//h5[@class="title"]/a')
            title = title_and_url.text
            if '东风' in title:
                try:
                    essay_url = title_and_url.attrib['url']
                except AttributeError:
                    print('还没有链接')

            else:
                continue
    else:
        print('请求失败，状态码%d' % response.raise_for_status())
except HTTPError:
    print('请求失败:HTTPError')

def request_info(url,cookies,headers):
    pass
