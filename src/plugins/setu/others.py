from typing import Optional
from random import choice
from httpx import AsyncClient, codes


# 来自 https://img.asmdh.com/
ASMDH_API = "https://img.asmdh.com/img.php"


async def get_asmdh():
    """链接爱尚随机图片API接口

    随机二次元，直接给了新浪图床链接，所以返回str不必处理直接发送即可

    Returns:
        str: 图片url
    """
    async with AsyncClient() as client:
        resp = await client.get(ASMDH_API, timeout=120)
    if resp.status_code != codes.OK:
        return resp.status_code
    return str(resp.url)


# 来自https://api.sunweihu.com/api/sjbz/
SJBZ_API = "https://api.sunweihu.com/api/sjbz/api.php"


async def get_sjbz(method: Optional[str]=None, lx: str='suiji') -> bytes:
    """链接API：https://api.sunweihu.com/api/sjbz/api.php
    
    基本都是当壁纸用的

    Args:
        method (str, optional): mobile(手机端),pc(电脑端), 不传入会在函数内部随机指定一个. Defaults to ''.
        lx (str, optional): dongman(动漫壁纸),meizi(美女壁纸),fengjing(风景壁纸),suiji(动漫和美女随机). Defaults to 'suiji'.

    Returns:
        bytes: 二进制图片
    """
    if not method:
        method = choice(('mobile', 'pc'))
    async with AsyncClient() as client:
        params = {
            'method': method,
            'lx': lx
        }
        resp = await client.get(SJBZ_API, params=params)
    if resp.status_code != codes.OK:
        return resp.status_code
    return resp.content


# 来自http://www.yunfada.cn/1535.html
NMB_API_ACG = "https://api.nmb.show/1985acg.php"
NMB_API_XJJ1 = "http://api.nmb.show/xiaojiejie1.php"
NMB_API_XJJ2 = "http://api.nmb.show/xiaojiejie2.php"


async def get_nmb(acg: bool) -> bytes:
    """连接api.nmb.show

    不是很涩的那种图

    Args:
        acg (bool): true则返回动漫图，否则是coser之类的那些

    Returns:
        bytes: 二进制图片
    """    

    api = NMB_API_ACG if acg else choice((NMB_API_XJJ1, NMB_API_XJJ2))

    async with AsyncClient(verify=False) as client:  # 要禁用证书检查不然会爆ssl证书错误
        resp = await client.get(api, timeout=90)
    if resp.status_code != codes.OK:
        return resp.status_code
    return resp.content


# 来自https://www.appmiu.com/circle/7013.html
# 这两个API都可以使用参数 return=img/json来返回图片或者json，但使用了几次好像不会和谐，所以直接用json吧
PW_PHOTO_API = "https://api.pixivweb.com/api.php"
PW_ANIME_API = "https://api.pixivweb.com/anime18r.php"


async def get_pw(acg: bool) -> str:
    """链接https://api.pixivweb.com/

    可以请求动漫或写真两种类型，可能包含R18，挺涩的(但也不一定)

    Args:
        acg (bool): true则返回动漫图，否则是coser之类的那些

    Returns:
        str: 图片url
    """    
    api = PW_ANIME_API if acg else PW_PHOTO_API
    param = {'return': 'json'}
    async with AsyncClient() as client:
        resp = await client.get(api, params=param, timeout=90)
    if resp.status_code != codes.OK:
        return resp.status_code
    return resp.json()['imgurl']


"""
※关于爱尚随机图片API
※虽然网站上写了用法但是测试之后变量都没生效，暂时只能以默认形式获取了，以下为备用

GET变量：return


取值：空/json/xml/302/url


普通浏览（不加参数）：


直接打开会返回一个只有一张图片的网页，仅适合普通浏览，无法用作背景等图片


json/xml接口：https://img.asmdh.com/img.php?return=json


返回相应的json/xml格式，带有图片地址的标准json/xml返回。


302跳转：https://img.asmdh.com/img.php?return=302


通过302返回直接跳转到图片源文件地址，可用作随机网页背景等方式


缺点：img等标签直接调用后无法直接查找到源文件地址（除非一直开着调试模式或抓包工具）


如果看到喜欢的图片只能通过右键保存下来。


URL返回：


仅返回一个URL，备用用途


GET变量：type


取值：bg


bg（即background）:


获取适合用作背景的随机图片（目前分辨率均为1920×1080，即16:9，适合大多数现代屏幕


如果不适合某些用户，请让他们换屏幕（笑））


联合变量：ctype


取值：acg、nature


acg：


获取动漫人物背景图片（全年龄段（笑））


nature：


获取环境背景图片
"""