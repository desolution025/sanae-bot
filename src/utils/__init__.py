import asyncio
from pathlib import Path
from typing import Union, Optional, Iterator
from io import BytesIO
import httpx
from imghdr import what
from nonebot.adapters.cqhttp.message import MessageSegment
from src.common.log import logger


async def save_img(url: str, filepath: Union[str, Path]):
    '''
    存储网络图片并将filepath文件名自动更正成正确的后缀
    '''
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=600)
    if resp.status_code != httpx.codes.OK:
        logger.error(f'Filed to request url: {url}')
        # print(f'Filed to request url: {url}')
        return
    if not isinstance(filepath, Path):
        filepath = Path(filepath)
    filepath.write_bytes(resp.content)
    if filepath.suffix != what(filepath):
        filepath.rename(filepath.with_suffix('.' + what(filepath)))

    
class ImageDownloader:
    """
    :Summary:

        网络图片资源下载器，可以并发下载网络图片并处理为BytesIO或本地文件

    :Args:

        ``**kw``: 可传递给client的参数

    """
    def __init__(self, **kw) -> None:
        self.client = httpx.AsyncClient(**kw)

    async def _unitrequest(self, url: str, **kw) -> Optional[httpx.Response]:
        """
        使用本单个异步请求防止链接超时而中断程序
        链接失败或请求不成功都会传出None
        """
        try:
            result = await self.client.get(url, **kw)
            if result.status_code != httpx.codes.OK:
                result == None
        except httpx.HTTPError as err:
            logger.error(f"{err}, when get url: {url}")
            result = None
        return result

    
    async def download(self, *urls, **kw) -> Iterator:
        """
        并发下载
        """
        tasks = []
        for url in urls:
            tasks.append(self._unitrequest(url, **kw))
        return await asyncio.gather(*tasks)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            logger.error(f'{exc_type}: {exc_val}')
        await self.client.aclose()




def imgseg(path=Union[str, Path]) -> MessageSegment:
    """
    :Summary:

        以本地文件路径生成一个可用的MessageSegment

    :Return:

        MessageSegment(image类型)
    """
    return 'file:///' + str(path)


if __name__ == "__main__":
    asyncio.run(save_img('https://www.baidu.com/img/flexible/logo/pc/result.png', 'dnmd'))