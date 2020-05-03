import pandas as pd

datas ={

    'baidu': 
        [
            'https://baijiahao.baidu.com/',
            'https://baijiahao.baidu.com/builder/rc/edit?type=news&app_id=1591384705840207',
            'https://baijiahao.baidu.com/builder/rc/content?type=&collection=&pageSize=10&currentPage=1&search=&app_id=1591384705840207',
            '13601135657','CYTcyt0910','百家号'
        ],
    
    'yidianzixun': 
        [
            'https://mp.yidianzixun.com/',
            'https://mp.yidianzixun.com/#/Writing/articleEditor',
            'https://mp.yidianzixun.com/#/ArticleManual/original/publish',
            '13601135657','CYTcyt0910','一点资讯'
        ],

    'sina': 
        [
            'http://mp.sina.com.cn/',
            'http://mp.sina.com.cn/main/editor?vt=4#/SendArt/Edit',
            'http://mp.sina.com.cn/#/ContentList',
            '13601135657','GBNgbn22222','新浪看点'
        ],

    'sohu': 
        [
            'http://mp.sohu.com',
            'https://mp.sohu.com/mpfe/v3/main/news/addarticle?contentStatus=1',
            'https://mp.sohu.com/mpfe/v3/main/news/articlelist',
            '346764791','GBNgbn22222','搜狐号'
        ],

    '163':
        [
            'http://mp.163.com/',
            'http://mp.163.com/article/postpage/W8567100657272114912?wemediaId=W8567100657272114912',
            'http://mp.163.com/index.html#/article/manage?wemediaId=W8567100657272114912',
            'gbngbn@126.com','CYTcyt22222','网易号'
        ],#标题字数在11-30
    
    'dayu':
        [
            'https://mp.dayu.com/',
            'https://mp.dayu.com/dashboard/article/write?spm=a2s0i.db_index.menu.4.15fb3caaD52hiw',
            'https://mp.dayu.com/dashboard/contents?spm=a2s0i.db_article_write.menu.6.1c7d3caanT1Ldh',
            '346764791@qq.com','GBNgbn22222','大鱼号'
        ],

    'ifeng':
        [
            'http://mp.ifeng.com/login',
            'https://mp.ifeng.com/publish/article',
            'http://fhh.ifeng.com/manage/originalArticle',
            '346764791','GBNgbn22222','大风号'
        ],

    'youcheyihou':
        [
            'http://mp.youcheyihou.com',
            'http://mp.youcheyihou.com/#/article-edit',
            'http://mp.youcheyihou.com/#/article-original',
            'bangninggongzuoshi','GBNgbn22222','有车号'
        ],

    'qutoutiao':
        [
            'https://mp.qutoutiao.net/',
            'https://mp.qutoutiao.net/publish-content/article',
            'https://mp.qutoutiao.net/content-manage/article?status=&page=1&title=&submemberid=&nickname=&start_date=&end_date=&isMotherMember=false',
            '13601135657','GBNgbn22222','趣头条'
        ],

    'weibo':
        [
            'https://weibo.com/',
            'https://card.weibo.com/article/v3/editor#/draft',
            'https://weibo.com/5646432272/profile?rightmod=1&wvr=6&mod=personinfo&is_all=1',
            '13601135657','GBNgbn22222','新浪微博'
        ],#建议用密码登录

    'toutiao':
        [
            'https://mp.toutiao.com/',
            'https://mp.toutiao.com/profile_v3/graphic/publish',
            'https://mp.toutiao.com/profile_v3/graphic/articles',
            '13601135657','GBNgbn22222','头条号'
        ],#手机验证
    
    'autohome': 
        [
            'https://chejiahao.autohome.com.cn/My',
            'https://chejiahao.autohome.com.cn/My',#'https://chejiahao.autohome.com.cn/My/AuthorArticles/add/0?r=637112680387173204#pvareaid=2808351',
            'https://chejiahao.autohome.com.cn/My/Info?r=637112680463379219',
            '帮宁工作室','GBNgbn22222','车家号'
        ],#登录有验证，图片需要大与560*315，长宽均大于

    'maiche':
        [
            'http://media.maiche.com/',
            'http://media.maiche.com/manage/fun/publish.html',
            'http://media.maiche.com/manage/fun/article.html',
            '13601135657','GBNgbn22222','车友号'
        ],

    'zhihu':
        [
            'https://www.zhihu.com/',
            'https://zhuanlan.zhihu.com/write',
            'https://www.zhihu.com/people/ge-bang-zhu/posts',
            '13601135657', 'GBNgbn22222','知乎'
        ],

    'qq':
        [
            '',#https://om.qq.com/article/index
            '',
            'https://kuaibao.qq.com/s/MEDIANEWSLIST?chlid=6188308&refer=',
            '346764791','GBNgbn22222','企鹅号',
        ],

    'pcauto':
        [
            'https://hj.pcauto.com.cn/my/',
            'https://hj.pcauto.com.cn/publish/',
            'https://hj.pcauto.com.cn/my/article/99/',
            '13601135657','GBNgbn22222','太平洋号'
        ],

    'cheshi':
        [
            '',#http://cheshihao.cheshi.com/back/index
            '',#http://cheshihao.cheshi.com/back/add/article.html
            'http://cheshihao.cheshi.com/back/list/article/all/1.html',
            '13601135657','GBNgbn22222','车市号'
        ],
    
    'yiche':
        [
            'http://mp.yiche.com/',
            'http://mp.yiche.com/article',
            'http://mp.yiche.com/manage/contentManage',
            '帮宁工作室','GBNgbn22222','易车号'
        ],
    
}

def get_acount_date(datas=datas):
    return pd.DataFrame(datas,index=['log','publish','query','account','code','name'])


if __name__ =='__main__':
    print(get_acount_date())