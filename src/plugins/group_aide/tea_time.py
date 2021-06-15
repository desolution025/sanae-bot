from random import choice, shuffle
from pathlib import Path
import asyncio

from nonebot import require, get_bots
from nonebot_adapter_gocq.exception import ActionFailed

from src.common import logger, RESPATH
from src.common.rules import group_func_off, sv_sw
from src.common.verify import Enable_Group, Group_Blocker
from src.utils import mediaseg


plugin_name = '饮茶提醒'
plugin_usage = '每日提醒饮茶小助手'


sv_sw(plugin_name, plugin_usage)  # 要运行一下把功能名装进去 TODO: 统一功能开关


TEATIME_NOTICE = (
    '喂！',
    '三点几嚟！',
    '做 做撚啊做！',
    '饮茶先啦！三点几嚟 饮茶先啦！',
    '做咁多都冇用嘅！',
    '老细唔锡你嘅嚟！',
    '喂饮下茶先啊！',
    '三点几嚟！',
    '做碌鸠啊做！' 
)


TEATIME_ATTACH = [mediaseg(f) for f in (Path(RESPATH)/'tea_time').glob('*.*')]  # 随机附加在后面一个媒体文件


scheduler = require('nonebot_plugin_apscheduler').scheduler


@scheduler.scheduled_job("cron", day_of_week='mon-sat', hour=15, id='3clock', misfire_grace_time=600)
async def three_clock():
    logger.info('Time to drink tea!!')
    for strid, bot in get_bots().items():
        groups : list = await bot.get_group_list()
        gids = [g['group_id'] for g in groups
        if Enable_Group(g['group_id']).check_enable() and Group_Blocker(g['group_id']).check_block()  # 未阻塞
        and plugin_name not in group_func_off[str(g['group_id'])]]  # 未关闭功能
        shuffle(gids)
        logger.info(f'Will Send {len(gids)} group(s): {str(gids)}')
        try:
            for g in gids:
                for msg in TEATIME_NOTICE:
                    await bot.send_group_msg(group_id=g, message=msg)
                    await asyncio.sleep(1.5)  # 防止消息发送间隔过短导致顺序错乱
                await bot.send_group_msg(group_id=g, message=choice(TEATIME_ATTACH))
                asyncio.sleep(15)  # 结束上一个群的发送开始发送下一个群的间隔
        except ActionFailed as err:
            logger.error(f'Maybe too intensive to send msg, cause error: {err}')


# 由用户自定义提醒功能时会需要这个添加、删除定时器的方式

# def sv_teatime(bot: Bot, event: GroupMessageEvent, state):
#     logger.debug(f'Got command {event.get_message().extract_plain_text().strip()}')
#     if event.get_message().extract_plain_text().strip() == plugin_name and\
#         isinstance(event, GroupMessageEvent) and event.sender.role in ('owner', 'admin'):
#         return True


# teatime_switch = MatcherGroup(type='message')
# teatime_on = teatime_switch.on_command('开启', rule=comman_rule(GroupMessageEvent))
# teatime_off = teatime_switch.on_command('关闭', rule=comman_rule(GroupMessageEvent))


# @teatime_on.handle()
# async def turn_tt_on(bot: Bot, event: GroupMessageEvent):
#     scheduler.add_job(test, 'cron', second='*/30', id='3clock', jitter=10)
#     logger.info(f'{event.group_id} turn the job 3clock On !')


# @teatime_off.handle()
# async def turn_tt_off(bot: Bot, event: GroupMessageEvent):
#     scheduler.remove_job('3clock')
#     logger.info(f'{event.group_id} turn the job 3clock Off !')


# tsttea = teatime_switch.on_command('饮茶')

# @tsttea.handle()
# async def tsteee(bot):
#     msg = choice(TEATIME_ATTACH)
#     logger.debug(str(msg))
#     await tsttea.finish(msg)