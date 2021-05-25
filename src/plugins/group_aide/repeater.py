from random import random

from nonebot.plugin import on

from src.common import Bot, GroupMessageEvent, Message, T_State, logger
from src.common.rules import sv_sw


plugin_name = '复读机'
plugin_usage = '''群复读机，一个人自己BB是不会触发的哦'''


repeat_rate = 0.25  # 复读概率，复读概率会随着次数递乘下去 (1-rate)**


cur_msg = {}  # 每个群装有的现在可能在复读的信息, 结构{gid: [当前正在重复的信息: str, 当前重复的次数: int, 当前复读过的id列表: list]}
"""
结构：{
    gid (str):{
        message (optinal[str]): 当前正在重复的信息,
        times (int): 已经复读的次数,
        uid_ls (Set[int]): 已经复读过的用户的ID
    }
    ...
}
"""
def store_talk(bot: Bot, event:GroupMessageEvent, state: T_State):

    if event.post_type not in ('message', 'message_sent') or event.message_type != 'group':
        return False

    # 消息不一致，重置存储
    if event.group_id not in cur_msg or event.raw_message != cur_msg[event.group_id]['message']:
        cur_msg[event.group_id] = {'message': event.raw_message, 'times': 0, 'uid_ls': {event.user_id}}
        logger.debug(f'{str(cur_msg)}')
        return False

    gr = cur_msg[event.group_id]

    # 复读过的人不在列表中，计算概率，如果是复读过的人会完全忽略消息，不刷新列表也不增加次数
    if event.user_id not in gr['uid_ls']:
    # if event.raw_message == gr['message']:
        gr['times'] += 1
        gr['uid_ls'].add(event.user_id)
        logger.debug(f'{str(cur_msg)}')
        if event.user_id != event.self_id:  # 可能是自己发送的消息不能触发自己复读
            c = random()
            r = (1 - repeat_rate) ** gr['times']
            # if random() > (1 - repeat_rate) ** gr['times']:
            logger.debug(f"c: {c}, r: {r}")
            if c > r:
                logger.debug(f'在第{gr["times"]}次触发了复读')
                state['raw_msg'] = gr['message']
                return True


repeater = on(rule=sv_sw(plugin_name, plugin_usage, '群助手')&store_talk)


@repeater.handle()
async def standby(bot: Bot, event: GroupMessageEvent, state: T_State):
    await repeater.finish(Message(state['raw_msg']))