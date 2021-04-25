import httpx
try:
    from src.common import logger
except ImportError:
    from loguru import logger


API = 'http://music.163.com/api/search/get/web'


class NetEase:
    """
    网易云搜索
    """
    def __init__(self) -> None:
        self.header = {
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip,deflate,sdch',
                    'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
                    'Connection': 'keep-alive',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Host': 'music.163.com',
                    'Referer': 'http://music.163.com/search/',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36'
                    }

        self.cookies = {
                    'appver': '1.5.2'
                    }

    async def search(self, s: str='', type: int=1, offset: int=0, num: int=5) -> httpx.Response:
        """
        搜索
        关于type:
            歌曲 1
            专辑 10
            歌手 100
            歌单 1000
            用户 1002
            mv 1004
            歌词 1006
            主播电台 1009
        Args:
            s (str): 搜索关键字
            type (int): 搜索类型
            offset (int): 偏移量(分页用)
            num (int): 搜索数量
        Returns:
            httpx.Response: [description]
        """
        datas = {
                's': s,
                'type': type,
                'offset': offset,
                'limit': num
                }
        async with httpx.AsyncClient() as client:
            result = await client.post(API, data=datas, timeout=30)
        return result


async def search_163(keyword: str, result_num: int=5):
    n = NetEase()
    song_list = []
    data = await n.search(keyword, num=result_num)
    if data and data.status_code == httpx.codes.OK:
        try:
            for item in data.json()['result']['songs'][:result_num]:
                song_list.append(
                    {
                        'name': item['name'],
                        'id': item['id'],
                        'artists': ' '.join(
                            [artist['name'] for artist in item['artists']]
                        ),
                        'type': '163'
                    }
                )
            return song_list
        except Exception as e:
            logger.error(f'获取网易云歌曲失败, 返回数据data={data}, 错误信息error={e}')
            return []
    return song_list


if __name__ == "__main__":
    import asyncio
    r = asyncio.run(search_163('凋叶棕', 5))
    if r:
        for song in r:
            print(song)