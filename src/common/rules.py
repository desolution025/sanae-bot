"""
定义可能会复用的通用规则，暂时包括：
分群功能开关规则
登录号被踢规则
群成员增加规则(剔除登录号加群)
群成员减少规则(剔除登录号被踢)
其他无特殊过滤的通用规则可使用common_rule
"""


from pathlib import Path
import ujson as json
from typing import Callable, Iterable
from functools import reduce
from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event, GroupMessageEvent


swfile = Path(__file__).parent/'group_func_off.json'
group_func_off = {}

"""
数据结构
{'gid': ['功能1', '功能2']}
"""
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

def sv_sw(name: str) -> Rule:
    """
    :Summary:
        
        使用此规则可以控制在不同群内的功能开关
    
    :Usage:
        
        传入规则时使用sv_sw(name: str)
        使用相同name的功能以相同的开关控制
    """
    if name not in func_ls:
        func_ls.append(name)
    async def _checker(bot: Bot, event: GroupMessageEvent, state: T_State):
        if hasattr(event, 'group_id') and str(event.group_id) in group_func_off\
            and name in group_func_off[str(event.group_id)]:
                return False
        else:
            return True
    return Rule(_checker)


def comman_rule(match_ev: Event, **kw) -> Callable:
    """
    :Summary:

        只是简单的匹配事件类型而没有其它过滤规则时可使用此函数输出通用规则

    :Args:

        ``match_ev``: 事件类型，从nonebot.adapters.cqhttp.event中导入相应类型
        ``**kw``: 可传入其他变量过滤时间子类型，如sub_type, honor_type等, 参数应为str或Iterable

    :Examples:

        ``example01``: comman_rule(PrivateMessageEvent)可过滤出私聊规则
        ``example02``: comman_rule(HonorNotifyEvent, honor_type="talkative")可过滤出龙王变更规则
        ``example03``: comman_rule(GroupDecreaseNoticeEvent, sub_type=("leave","kick"))可过滤出群成员减少规则，并且不包含登录号被踢("kick_me")的情况
    """
    async def ev_type_checker(bot:Bot, event: Event, state: T_State) -> bool:
        if isinstance(event, match_ev):
            if not kw:
                return True

            for k, v in kw.items():
                if isinstance(v, str):
                    if not hasattr(event, k):
                        raise AttributeError(f'EventType {type(event)} has no attribute {k}')
                    else:
                        return getattr(event, k) == v
                elif isinstance(v, Iterable):
                    # 对列表元素逐一检查是否包含event不存在的属性
                    if not reduce(lambda x, y: hasattr(event, x) and hasattr(event, y), v):
                        raise AttributeError(f'{v} contains {type(event)} non-existent attributes')
                    else:
                        return getattr(event, k) in v
                else:
                    raise AttributeError(f'Irregular incoming parameters: {kw}')
    return ev_type_checker