from pathlib import Path
from random import randint
from typing import Union
from io import BytesIO
from base64 import b64encode
from functools import partial

from PIL import Image
from imghdr import what


class Image_Handler:
    """把图像内容进行反和谐处理，并且支持存为base64编码或直接存入磁盘

    """

    def __init__(self, content: Union[str, Path, BytesIO, bytes], max_len: int=2048) -> None:
        """
        Args:
            content (Union[str, Path, BytesIO, bytes]): 图像内容
            max_len (int, optional): 反和谐后的图像长与宽不会大于该值. Defaults to 2048.
        """
        if isinstance(content, bytes):
            content = BytesIO(content)
        with Image.open(content) as self.img:
            self.img.thumbnail((max_len, max_len))
            self.changPixel()

    @staticmethod
    def randomcolor(dimension: int=3, *, alpha: int=0):
        """Random generate a color value

        Args:
            dimension (int): 3 o r4 corresponds to rgb and rgba. Defaults to 3.
            alpha (int, optional): Alpha value only use when dimension is 4. Defaults to 0.

        Returns:
            tuple: Color value
        """
        assert dimension in (3, 4), 'Only support rgb or rgba mode'
        pixel = (randint(0, 255), randint(0, 255), randint(0, 255))
        if dimension == 4:
            pixel += (alpha,)
        if alpha < 0 or alpha > 255:
            raise ValueError('Alpha value must between in 0~255')
        return pixel

    def changPixel(self):
        """
        Antishielding, over four pixels
        """
        width = self.img.width - 1
        height = self.img.height - 1
        px = self.img.load()
        if self.img.mode == 'RGBA':
            self.randomcolor = partial(self.randomcolor, dimension=4)
        for w in [0, width]:
            for h in [0, height]:
                px[w, h] = self.randomcolor()

    def save2file(self, filepath: Union[str, Path]):
        """将反和谐后的图像存为磁盘文件

            存储时后缀可以随意设置，但会自动修正为真实的后缀，所以返回的文件名称并不一定就等于输入的名称

        Args:
            filepath (Union[str, Path]): 要存储的文件路径

        Returns:
            Path: 和谐后的存储的文件路径
        """
        if self.img.mode == 'RGBA':
            self.img.save(filepath, format='PNG')
        else:
            self.img.save(filepath, format='JPEG', quality=90)
        real_suffix = f".{what(filepath).replace('jpeg', 'jpg')}"
        if not isinstance(filepath, Path):
            filepath = Path(filepath)
        
        # 真实后缀不符合当前后缀时自动修复
        if real_suffix != filepath.suffix.lower():
            filepath.rename(filepath.with_suffix(real_suffix))
        return filepath

    def save2b64(self):
        """将反和谐后的图像存为Base64编码字符串

        Returns:
            str: Base64字符串，可以直接使用MessageSegment.image构建片段
        """
        buffer = BytesIO()
        if self.img.mode == 'RGBA':
            self.img.save(buffer, format='png')
        else:
            self.img.save(buffer, format='jpeg', quality=90)
        return 'base64://' + b64encode(buffer.getvalue()).decode('utf-8')


if __name__ == "__main__":
    fp = "https://i.pixiv.cat/img-original/img/2021/02/01/19/00/00/87461567_p0.jpg"
    Image_Handler(fp).save2file("E:\Temp\check\87461567.ppp")