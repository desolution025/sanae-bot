from pathlib import Path
from typing import Union
import httpx
from imghdr import what
from nonebot.adapters.cqhttp.message import MessageSegment
# from src.common.log import logger


async def save_img(url: str, filepath: Union[str, Path]):
    '''
    存储网络图片并将filepath文件名自动更正成正确的后缀
    '''
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=600)
    if resp.status_code != httpx.codes.OK:
        # logger.error(f'Filed to request url: {url}')
        print(f'Filed to request url: {url}')
        return
    if not isinstance(filepath, Path):
        filepath = Path(filepath)
    filepath.write_bytes(resp.content)
    if filepath.suffix != what(filepath):
        filepath.rename(filepath.with_suffix('.' + what(filepath)))


def imgseg(path=Union[str, Path]) -> MessageSegment:
    """
    :Summary:

        以本地文件路径生成一个可用的MessageSegment

    :Return:

        MessageSegment(image类型)
    """
    return 'file:///' + str(path)


if __name__ == "__main__":
    import asyncio
    asyncio.run(save_img('https://www.baidu.com/img/flexible/logo/pc/result.png', 'dnmd'))