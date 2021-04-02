from collections import defaultdict
from pathlib import Path
import ujson as json
from .log import logger
from .easy_setting import *


#——————————————————sl设置——————————————————

sl_setting_file = Path(__file__).parent/'group_sl_set.json'
if not sl_setting_file.exists():
    with sl_setting_file.open('w', encoding='utf-8') as initj:
        json.dump({}, initj, indent=4)
with sl_setting_file.open(encoding='utf-8') as j:
    sl_settings = defaultdict(dict, json.load(j))


# 保存sl设置到磁盘，如果文件出错了会返回False
def save_sl():
    try:
        with sl_setting_file.open('w', encoding='utf-8') as j:
            json.dump(sl_settings, j, ensure_ascii=False, indent=4)
        return True
    except IOError as ioerr:
        logger.error(ioerr)
        return False