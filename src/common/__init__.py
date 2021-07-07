from collections import defaultdict
from pathlib import Path
import ujson as json
from typing import Dict

from nonebot import get_bots
from nonebot_adapter_gocq.bot import Bot

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


#——————————————————bot与群列表统计——————————————————


async def group_bot_map(*bots: Bot) -> Dict:
    """统计当前bots加了的群，反向映射为每个群里有存在的bot

    Returns:
        Dict[int: List[Bot]]: 群号为key，群内存在的bot列表为value的字典
    """

    # 如果不传入参数就自动获得所有连接的bot
    if not bots:
        bots = [bot for strid, bot in get_bots().items()]
    gbmap = defaultdict(set)
    # 把每个bot加过的群提取出来，以群为key添加各个bot到value中，value是bot的集合，可以自动去重
    for bot in bots:
        gids = map(lambda g: g["group_id"], await bot.get_group_list())  # 获取bot群列表，映射为gid迭代器
        for gid in gids:
            gbmap[gid].add(bot)
    # 把bot集合改成列表，否则不能在下一级函数中调用choice
    for gid in gbmap:
        gbmap[gid] = list(gbmap[gid])
    return dict(gbmap)


group_bot_dict = {}  # 群与bot映射列表


async def refresh_gb_dict():
    """刷新群与bot映射"""

    global group_bot_dict
    group_bot_dict = await group_bot_map()


def show_gb_dict():
    '''显示当前群内bot映射'''
    return group_bot_dict