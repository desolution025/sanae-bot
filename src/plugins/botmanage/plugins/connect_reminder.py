from random import choice
from datetime import datetime

from nonebot import on_notice, get_driver, get_bots
from nonebot_adapter_gocq.bot import Bot
from nonebot_adapter_gocq.event import GroupDecreaseNoticeEvent, GroupIncreaseNoticeEvent
# from nonebot import get_loaded_plugins

from src.common import refresh_gb_dict
from src.common.easy_setting import SUPERUSERS
from src.common.rules import comman_rule
from src.common.log import logger


_plugin_name = 'Bot连接提醒'


driver = get_driver()


# 上线提醒
@driver.on_bot_connect
async def online_remind(bot: Bot):
    # plugins = get_loaded_plugins()
    # normal_plguins = '\n'.join(map(lambda x: x.module.plugin_name, filter(lambda obj: hasattr(obj.module, 'plugin_name'), plugins)))
    # manager_pligins = '\n'.join(map(lambda x: x.module._plugin_name, filter(lambda obj: hasattr(obj.module, '_plugin_name'), plugins)))
    # msg = 'online desu\n[当前加载的插件]：\n' + normal_plguins + '\n[Bot管理插件]：\n' + manager_pligins
    msg = 'online desu'
    await refresh_gb_dict()
    for sps in SUPERUSERS:
        await bot.send_private_msg(user_id=sps, message=msg)


# 掉线提醒
@driver.on_bot_disconnect
async def ofl_rmd(bot: Bot):
    dc_time = datetime.now().time().strftime("%H:%M:%S")
    logger.critical(f'Bot {bot.self_id} disconnected')
    await refresh_gb_dict()

    ol_bots = [bt for strid, bt in get_bots().items()]
    if ol_bots:
        while ol_bots:
            notifier : Bot = choice(ol_bots)
            try:
                for su in SUPERUSERS:
                    await notifier.send_private_msg(user_id=su, message=f' {bot.self_id} disconnected at {dc_time}')
                break
            except BaseException as err:
                logger.error(f'Bot {notifier.self_id} failed to send offline notification: {err}')
                ol_bots.remove(notifier)
        else:
            logger.error(f'All bots failed to send notification!')

    else:
        logger.critical('There is no bot can send notification!')


# 被踢提醒
kicked = on_notice(rule=comman_rule(GroupDecreaseNoticeEvent, sub_type="kick_me"))

@kicked.handle()
async def kicked_remind(bot: Bot, event: GroupDecreaseNoticeEvent):
    msg = f'被 {event.operator_id} 踢出群 {event.group_id}'
    logger.info(msg)
    for su in SUPERUSERS:
        await bot.send_private_msg(user_id=su, message=msg)