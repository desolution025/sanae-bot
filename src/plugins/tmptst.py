from nonebot import on_command, on_startswith, on_endswith, on_keyword, get_bots, get_loaded_plugins
from nonebot.rule import to_me, Rule
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event
from nonebot.adapters.cqhttp.message import MessageSegment
from nonebot.typing import T_State
from src.common.log import logger


plugin_name = '测试模块'


starttst = on_startswith('开始', rule=to_me())

@starttst.handle()
async def tststart(bot: Bot, event:Event):
    msg = event.get_message()
    await starttst.send(msg)


tstargs = on_command('测试', priority=2)


@tstargs.handle()
async def tst_args(bot: Bot, event: Event, state: T_State):
    attrs = {
        'module': tstargs.module,
        'type': tstargs.type,
        'get_type': event.get_type(),
        'event_name': event.get_event_name(),
        'decription': event.get_event_description(),
        'user_id': event.get_user_id(),
        'message': event.get_message(),
        'is_tome': event.is_tome()
    }
    msg = ''
    for k, v in attrs.items():
        msg += k + ': ' + str(v) + '\n'
    gid = event.group_id
    sender = event.sender
    uid = sender.user_id
    strange_info = await bot.get_stranger_info(user_id=22)
    print(strange_info, type(strange_info))
    await tstargs.finish(f"{strange_info}, {type(strange_info)}")


tstcq = on_keyword(('测试CQ',))

@tstcq.handle()
async def tstcqcode(bot: Bot, event: Event):
    # cqcode = "[CQ:face,id=98]"  # 上报信息为array时不会转换字符串CQ码
    cqcode = {
        "type": "face",
        "data": {
            "id": "123"
            }
        }
    url = "https://www.runoob.com/wp-content/uploads/2016/04/json-dumps-loads.png"
    aa = MessageSegment.image(url)
    await tstcq.send(aa)


tstlog = on_command('日志')

@tstlog.handle()
async def tstlog_call(bot: Bot, event: Event):
    msg = event.get_message().extract_plain_text().strip()
    logger.warning(msg)
    await tstlog.finish('record log')


tstfinish = on_endswith('卧槽')

# 测试调用finish方法之后函数也会直接结束
@tstfinish.handle()
async def tst__finish(bot: Bot, event):
    bot = get_bots()
    for k in bot:
        print(k, type(k))
    # await tstfinish.finish(sps)


async def tstrule(bot: Bot, event: Event, state: T_State):
    if event.get_user_id() in bot.config.superusers:
        return True

tstrulecmd = on_command('测试规则', rule=tstrule)

@tstrulecmd.handle()
async def tstrulehandle(bot: Bot, event: Event):
    await tstrulecmd.finish('规则匹配')

from nonebot import matcher

misctst = on_command('testout')

@misctst.handle()
async def out(bot: Bot, event: Event):
    uid = event.sender.user_id
    sps = bot.config.superusers
    su = None
    for i in sps:
        su = i
    msg = f"{uid}  {type(uid)}\n{su}  {type(su)}"
    await misctst.finish(msg)


from nonebot import MatcherGroup


mg = MatcherGroup(type='message', priority=2)

tstmg = mg.on_command('tstgroup')

@tstmg.handle()
async def tstmghandle(bot: Bot):
    mathcers = mg.matchers

    msg = str([dir(m) for m in mathcers][0])
        
    await tstmg.finish(msg)


from random import random

async def randrule(bot, event, state):
    state['randnum'] = random()
    if state['randnum'] > 0.5:
        return True

rtst = on_command('tstrand', rule=randrule)

@rtst.handle()
async def randtst(bot: Bot, state: T_State):
    randnum = state['randnum']
    print(randnum)
    await rtst.finish(str(randnum))

from src.common.rules import sv_sw

tstsw = on_command('dddd', rule=sv_sw('开关dd'))

@tstsw.handle()
async def tstsw_(bot: Bot):
    await tstsw.finish('当前开启中')

tstsw2group = MatcherGroup(type='message', rule=sv_sw('开关2'))

tstsw2 = tstsw2group.on_command('开关2')

@tstsw2.handle()
async def tstsw2_(bot: Bot):
    await tstsw2.finish('sw2开启中')