from collections import defaultdict
from pathlib import Path
import ujson as json
from typing import Dict, Tuple, Union, Optional, Callable, Literal
from inspect import signature
from functools import wraps

from nonebot import get_bots
from nonebot.typing import T_Handler
from nonebot.matcher import Matcher
from nonebot_adapter_gocq.bot import Bot
from nonebot_adapter_gocq.message import MessageSegment, Message

from .log import logger
from .easy_setting import *
from src.utils import reply_header


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


def call_source(func: T_Handler, bot: Bot, event: MessageEvent, state: T_State, matcher: Matcher):
        """解析handler参数并赋予真实参数调用"""

        params = signature(func)
        _bot = params.parameters.get('bot')
        _event = params.parameters.get('event')
        _state = params.parameters.get('state')
        _matcher = params.parameters.get('matcher')
        args = []
        for i, param in enumerate([_bot, _event, _state, _matcher]):
            if param:
                args.append([bot, event, state, matcher][i])
        return func(*args)


def inputting_interaction(cancel_expression: Optional[Union[str, Tuple]]=None,
                        cancel_prompt: Optional[Union[str, Message, MessageSegment]]=None,
                        cancel_addition: Optional[Literal['at', 'reply']]=None,
                        verify_expression: Optional[Callable]=None,
                        verify_prompt: Optional[Union[str, Message, MessageSegment, Dict]]=None,
                        verify_addition: Optional[Literal['at', 'reply']]=None,
                        max_verfiy_times: int=3,
                        verify_cancel_prompt: Optional[Union[str, Message, MessageSegment]]=None,
                        verify_cancel_addition: Optional[Literal['at', 'reply']]=None,
                        ):
    """通用输入交互器

    使用这个装饰器让一个handler在执行命令之前对用户的输入检测是否是退出命令或输入参数不符合要求

    Args:
        cancel_expression (Optional[Union[str, Tuple]], optional): 退出语句. Defaults to None.
        cancel_prompt (Optional[Union[str, Message, MessageSegment]], optional): 触发退出后的提示. Defaults to None.
        cancel_addition (Optional[Literal['at', 'reply']], optional): 触发退出时是否附加操作，可选的有at和reply. Defaults to None.
        verify_expression (Optional[Callable], optional): 自定义验证函数，通常验证函数应返回bool，若返回其它值，则需要在verify_prompt中传入错误操作的提示字典，已匹配用户输入的错误类型. Defaults to None.
        verify_prompt (Optional[Union[str, Message, MessageSegment, Dict]], optional): 错误操作提示，如果传入为字典，则自定义验证函数中应有key匹配的值以对用户的操作错误类型做出相应的value提示. Defaults to None.
        verify_addition (Optional[Literal['at', 'reply']], optional): 触发错误输入时是否附加操作，与cancel_addition相同. Defaults to None.
        max_verfiy_times (int, optional): 最大错误提示次数，连续出错将不再继续对话，直接退出. Defaults to 3.
        verify_cancel_prompt (Optional[Union[str, Message, MessageSegment]], optional): 达到最大错误次数时退出操作的提示语句 Defaults to None.
        verify_cancel_addition (Optional[Literal['at', 'reply']], optional): 触发错误退出时是否附加操作，与cancel_addition相同. Defaults to None.
    """
    def deco(func: T_Handler):
        @wraps(func)
        async def wrapper(bot:Bot, event: MessageEvent, state: T_State, matcher: Matcher):
            arg = event.message.extract_plain_text().strip()
            
            # 验证退出命令
            if isinstance(cancel_expression, tuple) and arg in cancel_expression or isinstance(cancel_expression, str) and arg == cancel_expression:
                if cancel_prompt is None:
                    await matcher.finish()
                else:
                    if cancel_addition == 'at':
                        await matcher.finish(cancel_prompt, at_sender=True)
                    elif cancel_addition == 'reply':
                        await matcher.finish(reply_header(event, cancel_prompt))
                    else:
                        await matcher.finish(cancel_prompt)

            # 验证自定义验证函数
            if verify_expression is not None:
                result = call_source(verify_expression, bot, event, state, matcher)  # 获得自定义验证函数结果
                adopt = True
                if not isinstance(verify_prompt, dict) and not result:
                    adopt = False
                    rp = verify_prompt
                elif isinstance(verify_prompt, Dict) and result in verify_prompt:
                    adopt = False
                    rp = verify_prompt[result]
                
                # 未通过验证函数
                if not adopt:
                    if 'err_times' not in state:
                        state['err_times'] = max_verfiy_times
                    state['err_times'] -= 1
                    if state['err_times'] > 0:
                        if rp is None:
                            await matcher.reject()
                        else:
                            if verify_addition == 'at':
                                await matcher.reject(rp, at_sender=True)
                            elif verify_addition == 'reply':
                                await matcher.reject(reply_header(event, rp))
                            else:
                                await matcher.reject(rp)
                    else:
                        if verify_cancel_prompt is None:
                            await matcher.finish()
                        else:
                            if verify_cancel_addition == 'at':
                                await matcher.finish(verify_cancel_prompt, at_sender=True)
                            elif verify_cancel_addition == 'reply':
                                await matcher.finish(reply_header(event, verify_cancel_prompt))
                            else:
                                await matcher.finish(verify_cancel_prompt)

            await call_source(func, bot, event, state, matcher)
            
        return wrapper
    return deco