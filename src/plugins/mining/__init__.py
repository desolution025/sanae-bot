from functools import partial
from typing import Union

from nonebot import MatcherGroup
from nonebot.rule import ArgumentParser

from src.common import Bot, MessageEvent, GroupMessageEvent, MessageSegment, T_State, CANCEL_EXPRESSION
from src.common.rules import full_match
from src.common.levelsystem import UserLevel
from src.common.dbpool import QbotDB
from .mine import *
from src.utils import reply_header


plugin_name = '挖矿'
plugin_usage = ''


mining = MatcherGroup(type='message', priority=2)


open_mine = mining.on_message(rule=full_match('开矿场'))


@open_mine.handle()
async def can_start(bot: Bot, event: MessageEvent, state: T_State):
    uid = event.user_id
    user = UserLevel(uid)
    reply = partial(reply_header, event=event)
    
    # 小于三级或者资金不足200的用户不能开启矿场
    if user.level < 3:
        await open_mine.finish(reply('开发矿场最小需要3级，先作为开采者开采其它矿场主的矿洞吧~'))
    if user.fund < 200:
        await open_mine.finish(reply('开发矿场最少需要200的启动资金，金额充足时再成为矿场主吧~'))
    # 开发矿场数量超出限制
    if mc := mining_count(uid) >= upper_limit(user.fund):
        await open_mine.finish(reply(f'您当前已同时运作{mc}个矿场，提升等级可以增加同时运作矿场的数量哟~'))
    
    # 条件满足，询问投资数据
    state['user'] = user
    await open_mine.send(f'您当前资金为 {user.fund}，请输入需要为该矿场投入的资金\n(投入资金与该矿场产出率成正比，范围200-1000\n输入"取消"退出本操作)')


@open_mine.receive()
async def invest(bot: Bot, event: MessageEvent, state: T_State):
    arg = event.message.extract_plain_text().strip()
    if arg in CANCEL_EXPRESSION:
        await open_mine.finish('已退出开启矿场操作')

    if not arg.isdigit():
        await open_mine.reject('请输入200-1000内数字，输入"取消"退出本操作')
