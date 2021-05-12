from random import random

from nonebot.plugin import on
from nonebot_adapter_gocq.event import PrivateMessageSentEvent, GroupMessageSentEvent

from src.common import Bot, GroupMessageEvent, Message, T_State, logger
from src.common.rules import sv_sw


plugin_name = '复读机'
plugin_usage = '''复读机坏了，等修'''


repeat_rate = 0.3  # 复读概率，复读概率会随着次数递乘下去 (1-rate)**


cur_msg = {}  # 每个群装有的现在可能在复读的信息, 结构{gid: [当前正在重复的信息: str, 当前重复的次数: int, 当前复读过的id列表: list]}
"""
结构：{
    gid (str):{
        message (optinal[str]): 当前正在重复的信息,
        times (int): 已经复读的次数,
        uid_ls (list[int]): 已经复读过的用户的ID
    }
    ...
}
"""
def store_talk(bot: Bot, event:GroupMessageEvent, state: T_State):
    return False  # 暂时禁用掉
    if not isinstance(event, (GroupMessageEvent, GroupMessageSentEvent)):
        return False

    logger.debug(f'{isinstance(event, GroupMessageSentEvent)}')
    # 消息不一致或复读过的人重复复读，重置存储
    # if event.group_id not in cur_msg or event.raw_message != cur_msg[event.group_id]['message'] or event.group_id in cur_msg[event.group_id]['uid_ls']:
    logger.debug(f'{str(cur_msg)}')
    if event.group_id not in cur_msg or event.raw_message != cur_msg[event.group_id]['message']:
        cur_msg[event.group_id] = {'message': event.raw_message, 'times': 0, 'uid_ls': [event.user_id]}
        return False

    gr = cur_msg[event.group_id]
    gr['uid_ls'].append(event.user_id)

    # 消息一致且复读过的人不在列表中，计算概率
    # if event.raw_message == gr['message'] and event.user_id not in gr['uid_ls']:
    if event.raw_message == gr['message']:
        gr['times'] += 1
        gr['uid_ls'].append(event.user_id)
        c = random()
        r = (1 - repeat_rate) ** gr['times']
        # if random() > repeat_rate ** (1 - gr['times']):
        logger.debug(f"c: {c}, r: {r}")
        if c > r:
            logger.debug(f'在第{gr["times"]}次触发了复读')
            state['raw_msg'] = gr['message']
            return True


repeater = on(rule=sv_sw(plugin_name, plugin_usage, '群助手')&store_talk, priority=1, block=False)


@repeater.handle()
async def standby(bot: Bot, event: GroupMessageEvent, state: T_State):
    await repeater.finish(Message(state['raw_msg']))
    