"将平台域名特征字符串与平台的Web子类进行一个映射"

from web_class import Web,Bjh,Weibo,Sina,Sohu,W163,Dayu,Ifeng,Youche,Qtt,Toutiao,Ydzx,Cjh,Cheyou,Qq,Zhihu,\
    Tpy,Cheshi,Yiche

map_from_name_to_class = {
    'baidu': Bjh,
    'weibo': Weibo,
    'sina': Sina,
    'sohu': Sohu,
    '163': W163,
    'dayu': Dayu,
    'ifeng': Ifeng,
    'youcheyihou': Youche,
    'qutoutiao': Qtt,
    'toutiao': Toutiao,
    'yidianzixun': Ydzx,
    'autohome': Cjh,
    'maiche': Cheyou,
    'zhihu': Zhihu,
    'qq':Qq,
    'pcauto':Tpy,
    'cheshi':Cheshi,
    'yiche':Yiche,
}
def map_name_class(name):
    try:
        return map_from_name_to_class[name]
    except KeyError:
        print('该平台代号没有对应的类。\n')

