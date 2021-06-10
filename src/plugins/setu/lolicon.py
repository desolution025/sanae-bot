import httpx
try:
    from src.common import logger
except ImportError:
    from loguru import logger


API = 'https://api.lolicon.app/setu/v1'


async def get_lolicon(kwd: str='', r18: int=0, num: int=1, size1200: bool=False) -> dict:
    """
    :Summary:

        连接loliconAPI的异步函数

    :Args:

        * ``kwd``: 若指定关键字，将会返回从插画标题、作者、标签中模糊搜索的结果
        * ``r18``: 0为非 R18，1为 R18，2为混合
        * ``num``: 一次返回的结果数量，范围为1到10，不提供 APIKEY 时固定为1；在指定关键字的情况下，结果数量可能会不足指定的数量
        * ``size1200``: 是否使用 master_1200 缩略图，即长或宽最大为 1200px 的缩略图，以节省流量或提升加载速度（某些原图的大小可以达到十几MB）

    :Returns:
        json: {
            ``code``: int 返回码，可能值详见后续部分
            ``msg``: string 错误信息之类的
            ``count``: int 结果数
            ``data``: list[dict(setu)] 色图数据列表
            }

            ``setu``: {
                ``pid``: int 作品 PID
                ``p``: int 作品所在 P
                ``uid``: int 作者 UID
                ``title``: string 作品标题
                ``author``: sting 作者名（入库时，并过滤掉 @ 及其后内容）
                ``url``: string 图片链接（可能存在有些作品因修改或删除而导致 404 的情况）
                ``r18``: bool 是否 R18（在色图库中的分类，并非作者标识的 R18）
                ``width``: int 原图宽度 px
                ``height``: int 原图高度 px
                ``tags``: list[string] 作品标签，包含标签的中文翻译（有的话）
                }
            
            ``code``:{
                ``-1``: 内部错误，请向 i@loli.best 反馈
                ``0``: 成功
                ``404``: 找不到符合关键字的色图
            }

    """
    async with httpx.AsyncClient() as client:
        params = {
                'r18': r18,
                'keyword': kwd,
                'num': num,
                'size1200': size1200
                }
        resp = await client.get(API, params=params, timeout=120)
        result = resp.json()
        logger.debug(result)

    return result


def get_1200(url: str) -> str:
    """
    :Summary:

        通过原始url获得master1200的缩略图以提升传输速度

    :Arg:

        ``url``: 原始链接
    
    :Return:

        master1200缩略图url
    """
    return url.replace('original', 'master')[:-4] + '_master1200.jpg'


if __name__ == "__main__":
    print(get_1200("https://i.pixiv.cat/img-original/img/2020/03/15/19/17/46/80139606_p1.jpg"))