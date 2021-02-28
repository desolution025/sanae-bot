import asyncio
from pathlib import Path
from typing import Union
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
    real_suffix = f".{what(filepath).replace('jpeg', 'jpg')}"
    if real_suffix != filepath.suffix.lower():
        filepath.rename(filepath.with_suffix(real_suffix))
    return filepath


def imgseg(path=Union[str, Path]) -> MessageSegment:
    """以本地文件图片创建一个可直接发送的MessageSegment

        确认不会被和谐的图片使用此方法，否则使用antishieding模块中的Image_Hander来处理

    Args:
        path (str, Path): 文件路径. Defaults to Union[str, Path].

    Returns:
        MessageSegment: image类型
    """
    return 'file:///' + str(path)


if __name__ == "__main__":
    asyncio.run(save_img('https://www.baidu.com/img/flexible/logo/pc/result.png', 'dnmd'))