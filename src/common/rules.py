'''
定义一些可能会复用的通用规则，暂时包括：
分群功能开关规则
TODO:
戳一戳规则
群荣誉变更规则
入群规则
退群规则
管理踢人规则
加好友请求规则
加群请求规则
管理员变动规则
撤回消息规则
'''


from pathlib import Path
import ujson as json
from nonebot.rule import Rule
from typing import Callable
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import (
    GroupMessageEvent,
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent)


swfile = Path(__file__).parent/'group_func_off.json'
group_func_off = {}

'''
数据结构
{'gid': ['功能1', '功能2']}
'''
def store_sw():
    '''
    将群功能开关记录在json文件上的函数
    '''
    with swfile.open('w', encoding='utf-8') as j:
        json.dump(group_func_off, j, ensure_ascii=False, indent=4)

if not swfile.exists():
    store_sw()

with swfile.open(encoding='utf-8') as j:
    group_func_off = json.load(j)
    
func_ls = []  # 存储所有功能名字的列表，建立功能开关时自动存入，用来查询是否是真实存在的功能

def sv_sw(name: str) -> Callable:
    '''
    使用此规则可以控制在不同群内的功能开关
    传入规则时使用sv_sw(name: str)
    使用相同name的功能以相同的开关控制
    '''
    if name not in func_ls:
        func_ls.append(name)
    async def _checker(bot: Bot, event: GroupMessageEvent, state: T_State):
        if hasattr(event, 'group_id') and str(event.group_id) in group_func_off\
            and name in group_func_off[str(event.group_id)]:
                return False
        else:
            return True
    return Rule(_checker)


async def kick_me(bot: Bot, event: GroupDecreaseNoticeEvent, state: T_State) -> bool:
    '''
    登录号被踢出规则
    '''
    if isinstance(event, GroupDecreaseNoticeEvent) and event.sub_type == 'kick_me':
        return True


async def group_increase(bot: Bot, event: GroupIncreaseNoticeEvent, state: T_State) -> bool:
    '''
    群成员增加规则，剔除了bot加群的情况
    '''
    if isinstance(event, GroupIncreaseNoticeEvent) and event.user_id != event.self_id:
        return True