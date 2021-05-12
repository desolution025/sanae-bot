from random import randint
from collections import defaultdict
from datetime import datetime
from asyncio import sleep as asleep

from nonebot import MatcherGroup
from nonebot_adapter_gocq.event import GroupRecallNoticeEvent
from nonebot_adapter_gocq.exception import ActionFailed
from nonebot_adapter_gocq.utils import unescape

from src.common import Bot, GroupMessageEvent, Message, logger
from src.common.rules import sv_sw, comman_rule
from src.utils import reply_header


plugin_name = '防撤回'
plugin_usage = '[N号记录是什么] N换成撤回时返回的记录号则会返回被撤回的内容，注意不要带标点\n※※不喜欢的话使用关闭功能开关就好'


antirecall = MatcherGroup(rule=sv_sw(plugin_name, plugin_usage, hierarchy='群助手'))


ta_map = {'male':'他', 'female':'她','unknown':'它'}
recalled = defaultdict(dict)  # 存储每个群的每个撤回消息的字典
"""
结构：group_id:
        {fake_id:
            [msg_id: int, passive: bool, time]
        }
"""


def store_recall(gid: int, fake_id: int, message_id: int, passive: bool, time: int, max_length: int=20):
    """
    存储群撤回的记录的信息

    Args:
        gid (int): 群号
        fake_id (int): 伪id，用来显示给用户调用
        message_id (int): 真实id，与伪id一一对应
        passive (bool): 被动，True则为被管理员撤回而非主动撤回
        time (int): 撤回时的时间戳
        max_length (int, optional): 列表中存储的最大值，超过此值则会删除最早记录的id. Defaults to 20.
    """
    rc_ls : dict = recalled[gid]
    rc_ls[fake_id] = [message_id, passive, time]
    # 重新存储键值刷新字典排序
    if len(rc_ls) > max_length:
        reverse_keys = reversed(rc_ls)
        _tmp_dict = {}
        for k in reverse_keys:  
            _tmp_dict[k] = rc_ls[k]
            _tmp_dict.popitem()
        recalled[gid] = _tmp_dict


recall_trigger = antirecall.on_notice(rule=sv_sw(plugin_name, plugin_usage, hierarchy='其它')&comman_rule(GroupRecallNoticeEvent))


@recall_trigger.handle()
async def got_recall(bot: Bot, event: GroupRecallNoticeEvent):
    while True:
        if (fake_id := randint(10, 999)) not in recalled[event.group_id]:  # 由于真实消息id过长并且有负数造成调用混淆所以使用伪id进行对应
            break
    passive = event.user_id != event.operator_id  # 主动撤回还是被管理撤回
    store_recall(event.group_id, fake_id, event.message_id, passive, event.time)
    litigant_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
    litigant_name = litigant_info["card"] or litigant_info["nickname"] or str(event.user_id)

    if passive:
        operator_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.operator_id)
        operator_name = operator_info["card"] or operator_info["nickname"] or str(event.operator_id)
        msg = f'{operator_name}撤回了被{litigant_name}掌握的{fake_id}号援交证据！'
    else:
        msg = f'{litigant_name}撤回了{ta_map[litigant_info["sex"]]}的{fake_id}号援交记录!'

    await recall_trigger.finish(msg)


recorder = antirecall.on_endswith('号记录是什么', rule=sv_sw(plugin_name, plugin_usage, hierarchy='其它')&comman_rule(GroupMessageEvent))


@recorder.handle()
async def show_record(bot: Bot, event: GroupMessageEvent):
    arg = str(event.message).split('号记录')[0]
    if not arg.isdigit():
        await recorder.finish(reply_header(event, '哪有这种代号的记录啊？！'))
    fake_id = int(arg)
    if fake_id not in recalled[event.group_id]:
        await recorder.finish(reply_header(event, '这条记录不存在或者因为太久所以被消除了~'))
    msg_id, passive, timestamp = recalled[event.group_id][fake_id]
    try:
        msginfo = await bot.get_msg(message_id=msg_id)
        logger.debug(f"Got recalled message({type(msginfo['message'])}): {str(msginfo['message'])}")
    except ActionFailed:
        await recorder.finish(reply_header(event, '这条记录不存在或者因为太久所以被消除了~'))
    for seg in msginfo["message"]:
        logger.debug(f'Check type of segment: {seg}\n{seg["type"]}')
        if seg['type'] not in ('text', 'face', 'image', 'at', 'reply'):  # 可以夹在普通消息框里的片段
            can_append = False
            break
    else:
        can_append = True

    time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    try:
        litigant_info = await bot.get_group_member_info(group_id=event.group_id, user_id=msginfo["sender"]["user_id"])
        name = litigant_info["card"] or litigant_info["nickname"] or str(litigant_info["user_id"])
    except ActionFailed:
        name = msginfo["sender"]["user_id"]  # 没获取到的话可能群员退群了
    if passive:
        header = f"{name}在{time}被撤回了：\n"
    else:
        header = f"{name}在{time}撤回了：\n"

    if can_append:
        await recorder.finish(Message(header) + (Message(msginfo["message"])))
    else:
        await recorder.send(Message(header))
        await asleep(1)
        # await recorder.finish(msginfo["message"])

        await recorder.finish(Message(msginfo["raw_message"]))