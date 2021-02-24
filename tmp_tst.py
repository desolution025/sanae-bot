from PIL import Image
from pathlib import Path
from math import ceil


def resize_img(imgpath: Path, max_len: int) -> Image:
    with imgpath.open('rb'):
        img = Image.open(imgpath)

        width = img.width
        height = img.height
        if width <= max_len and height <= max_len:  # 如果长和宽都比max_len小就直接返回了
            return img

        if width > height:
            rw = max_len
            rh = ceil(rw * height / width)
        else:
            rh = max_len
            rw = ceil(rh * width / height)

        resizedimg = img.resize((rw, rh), resample=Image.BICUBIC, reducing_gap=3.0)
    
    return resizedimg


fp = "E:\Temp\Cache_-3b0737133eb86502__thumbnail_thumbnail.jpg"

nfp = Path(fp).parent/(Path(fp).stem + "_thumbnail" + Path(fp).suffix)
with Image.open(fp) as img:
    img.thumbnail((1200,1200), reducing_gap=2.0, resample=Image.BICUBIC)
    img.save(nfp, format='jpeg', quality=100)


# img = resize_img(Path(fp), 1200)

# img.save(nfp, format='jpeg', quality=100)