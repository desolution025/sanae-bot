from random import random
from collections import defaultdict

from nonebot.plugin import on_message

from src.common import Bot, GroupMessageEvent, Message
from src.common.rules import sv_sw


plugin_name = '复读机'
plugin_usage = '''复读机坏了，等修'''


cur_msg = defaultdict(list)  # 每个群装有的现在可能在复读的信息, 结构{gid: [当前重复数量，当前信息]}


repeater = on_message(rule=sv_sw(plugin_name, plugin_usage, '群助手'), priority=5, block=False)


@repeater.handle()
async def standby(bot: Bot, event: GroupMessageEvent):
    if event.group_id not in cur_msg:
        cur_msg[event.group_id] = [1, event.raw_message]
        return
    