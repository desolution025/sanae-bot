from random import choice

from nonebot import on_notice
from nonebot.rule import Rule
from nonebot_adapter_gocq.event import GroupPokeNotifyEvent

from src.common import Bot, MessageSegment, SUPERUSERS
from src.common.rules import sv_sw, comman_rule


plugin_name = '夏姬八戳'
plugin_usage = '戳就是了'


pokeme = on_notice(rule=Rule(comman_rule(GroupPokeNotifyEvent))&sv_sw(plugin_name, plugin_usage, '群助手'))


@pokeme.handle()
async def poke_reply(bot: Bot, event: GroupPokeNotifyEvent):
    sponsor = event.user_id
    target = event.target_id
    botself = event.self_id

    if sponsor == botself:
        await pokeme.finish()  # 如果戳一戳由bot自己发起则无效，防止循环戳
    if target in SUPERUSERS:
        await pokeme.finish(MessageSegment(type='poke', data={'qq': event.user_id}))
    if target == botself:
        member_list = await bot.get_group_member_list(group_id=event.group_id)
        member_qq_list = list(map(lambda x: x['user_id'], member_list))
        target_id = choice(member_qq_list)
        await pokeme.send(MessageSegment(type='poke', data={'qq': target_id}))
        if target_id == botself:
            await pokeme.finish('啊~竟然戳中了我自己！')