from random import randint
from collections import defaultdict

from nonebot import MatcherGroup
from nonebot.plugin import on_notice
from nonebot.adapters.cqhttp.event import GroupRecallNoticeEvent

from src.common.rules import sv_sw, comman_rule
from src.common import Bot, GroupMessageEvent


plugin_name = '防撤回'
plugin_usage = '[n号记录是什么] n换成撤回时返回的记录号则会返回被撤回的内容，注意不要带标点'


antirecall = MatcherGroup(rule=sv_sw(plugin_name, plugin_usage))


ta_map = {'male':'他', 'female':'她','unknown':'它'}
recalled = {}  # 存储每个群的每个撤回消息的字典
"""
结构：group_id:
        {fake_id:
            {msg_id: int,
            passive: bool
            }
        }
"""


def store_recall(gid: int, fake_id: int, message_id: int, passive: bool, max_length: int=20):
    """
    存储群撤回的记录的信息

    Args:
        gid (int): 群号
        fake_id (int): 伪id，用来显示给用户调用
        message_id (int): 真实id，与伪id一一对应
        passive (bool): 被动，True则为被管理员撤回而非主动撤回
        max_length (int, optional): 列表中存储的最大值，超过此值则会删除最早记录的id. Defaults to 20.
    """
    rc_ls : dict = recalled[gid]
    rc_ls[fake_id] = {"msg_id": message_id, "passive": passive}
    # 重新存储键值刷新字典排序
    if len(rc_ls) > max_length:
        reverse_keys = reversed(rc_ls)
        _tmp_dict = {}
        for k in reverse_keys:  
            _tmp_dict[k] = rc_ls[k]
            _tmp_dict.popitem()
        recalled[gid] = _tmp_dict



recall_trigger = antirecall.on_notice(rule=comman_rule(GroupRecallNoticeEvent))


@recall_trigger.handle()
async def got_recall(bot: Bot, event: GroupRecallNoticeEvent):
    while True:
        if fake_id := randint(10, 999) not in recalled[event.group_id]:  # 由于真实消息id过长并且有负数造成调用混淆所以使用伪id进行对应
            break
    passive = event.user_id != event.operator_id  # 主动撤回还是被管理撤回
    store_recall(event.group_id, fake_id, event.message_id, passive)
    litigant_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
    litigant_name = litigant_info["card"] or litigant_info["nickname"] or str(event.user_id)

    if passive:
        operator_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.operator_id)
        operator_name = operator_info["card"] or operator_info["nickname"] or str(event.operator_id)
        msg = f'{operator_name}撤回了被{litigant_name}掌握的{fake_id}号援交证据！'
    else:
        msg = f'{litigant_name}撤回了{ta_map[litigant_info["sex"]]}的{fake_id}号援交记录!'

    await recall_trigger.finish(msg)


recorder = antirecall.on_endswith('号记录是什么', rule=comman_rule(GroupMessageEvent))


@recorder.handle()
async def show_record(bot: Bot, event: GroupMessageEvent):
    print(str(event.message))