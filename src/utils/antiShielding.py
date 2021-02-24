from pathlib import Path
from random import randint
from typing import Union
from io import BytesIO
from base64 import b64encode
from PIL import Image


def resize_img(imgpath: Path, max_len: int):
    """
    :Summary:

        Resize image when the width or height of it beyond max_len
    
    :Args:

        ``imgpath``: Iamgepath, must be a pathlib.Path object
        ``max_len``: Max width or height with this argument
    """
    with imgpath.open('rb'):
        img = Image.open(imgpath)

        width = img.width
        height = img.height
        if width <= max_len and height <= max_len:  # 如果长和宽都比max_len小就直接返回了
            return img

        if width > height:
            rw = max_len
            rh = round(rw * height / width)
        else:
            rh = max_len
            rw = round(rh * width / height)

        resizedimg = img.resize((rw, rh))
    
    return resizedimg


# change pixel color
def randomcolor():
    return (randint(0, 255), randint(0, 255), randint(0, 255))


def changPixel(img: Image.Image) -> Image.Image:
    """
    Antishielding, over four pixels
    """
    width = img.width - 1
    height = img.height - 1
    px = img.load()
    px[0,0] = randomcolor()
    px[width, 0] = randomcolor()
    px[width, height] = randomcolor()
    px[0, height] = randomcolor()
    
    return img


def handleimage(imgPath: Union[str, Path], max_len: int=2048, suffix: str=' (antishieded).jpg', outpath: str=r"./res/images/setu/antishieded") -> Path:
    """
    正常图片进行反和谐处理，超出尺寸最大值的图片重定尺寸最大为限制值，如果resize过直接运行反和谐
    """
    outfile = Path(outpath)/(Path(imgPath).stem + suffix)
    with Image.open(imgPath) as img:
        if img.width < max_len and img.height < max_len:
            img = changPixel(img)
        elif outfile.exists():  # 已经存在的情况下说明resize过了，直接用这个文件进行反和谐
            with Image.open(outfile) as outim:
                img = changPixel(outim)
        else:
            img.thumbnail((max_len, max_len))
        
        # if not outfile.exists():
        img.save(outfile, format='jpeg', quality=90)
    return outfile


def gen_b64(imgPath: Union[str, Path], max_len = 2048, quality: int=90) -> str:
    """
    生成已经反和谐过的Base64编码字符串
    """
    with Image.open(imgPath) as img:
        img = changPixel(img)
        buffer = BytesIO()
        img.save(buffer, format='jpeg', quality=quality)
    return 'base64://' + b64encode(buffer.getvalue()).decode('utf-8')


if __name__ == "__main__":
    fp = "E:\Temp\Cache_-3b0737133eb86502_.jpg"
    handleimage(fp, 1200, outpath="E:\Temp")