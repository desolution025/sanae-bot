import httpx


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

    async def search(self, s: str, type: int, offset: int, num: int) -> httpx.Response:
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
            


if __name__ == "__main__":
    r = NetEase().search('凋叶棕', )