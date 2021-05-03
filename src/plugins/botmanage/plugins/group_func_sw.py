from nonebot import on_command
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent as Event
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.permission import GROUP

from src.common import SUPERUSERS
from src.common.rules import group_func_off, store_sw, func_ls


_plugin_name = '分群功能开关'


func_on = on_command('开启', aliases={'启用'}, permission=GROUP)

@func_on.handle()
async def turn_func_on(bot: Bot, event: Event):
    fname = event.get_message().extract_plain_text().strip()
    if not fname:
        return
    if fname not in func_ls:
        await func_on.finish(f'没有找到名字为<{fname}>的功能')
    gid = str(event.group_id)
    if gid not in group_func_off:
        group_func_off[gid] = []
    if fname not in group_func_off[gid]:
        await func_on.finish(f'这个功能已经是开启状态了哦~')
    else:
        if event.sender.role not in ('owner', 'admin') and event.user_id not in SUPERUSERS:
            await func_on.finish(f'请联系管理员开启此功能')
        group_func_off[gid].remove(fname)
        store_sw()
        await func_on.finish(f'已启用功能<{fname}>')


func_off = on_command('停用', aliases={'关闭'}, permission=GROUP)

@func_off.handle()
async def turn_func_on(bot: Bot, event: Event):
    fname = event.get_message().extract_plain_text().strip()
    if not fname:
        return
    if fname not in func_ls:
        await func_on.finish(f'没有找到名字为<{fname}>的功能')
    gid = str(event.group_id)
    if gid not in group_func_off:
        group_func_off[gid] = []
    if fname in group_func_off[gid]:
        await func_on.finish(f'这个功能已经是关闭状态了哦~')
    else:
        if event.sender.role not in ('owner', 'admin') and event.user_id not in SUPERUSERS:
            await func_on.finish(f'请联系管理员关闭此功能')
        group_func_off[gid].append(fname)
        store_sw()
        await func_on.finish(f'已停用功能<{fname}>')