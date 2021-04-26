from nonebot import on_metaevent, on_notice
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import LifecycleMetaEvent, GroupDecreaseNoticeEvent
from nonebot.typing import T_State
from nonebot import get_loaded_plugins

from src.common.easy_setting import SUPERUSERS
from src.common.rules import comman_rule
from src.common.log import logger


plugin_name = '上线提醒'


# 上线提醒
online = on_metaevent(rule=comman_rule(LifecycleMetaEvent, sub_type="connect"))

@online.handle()
async def online_remind(bot: Bot):
    plugins = get_loaded_plugins()
    normal_plguins = '\n'.join(map(lambda x: x.module.plugin_name, filter(lambda obj: hasattr(obj.module, 'plugin_name'), plugins)))
    manager_pligins = '\n'.join(map(lambda x: x.module.plugin_name, filter(lambda obj: hasattr(obj.module, '_plugin_name'), plugins)))
    msg = 'online desu\n当前加载的插件：\n' + normal_plguins + '\nBot管理插件：\n' + manager_pligins
    # msg = 'online desu\n当前加载的插件：\n' + '\n'.join(map(lambda x: x.module.plugin_name, filter(lambda obj: hasattr(obj.module, 'plugin_name'), plugins)))
    # TODO: 只有维护组可见的插件帮助变量在前面加_
    for sps in SUPERUSERS:
        await bot.send_private_msg(user_id=sps, message=msg)


# 被踢提醒
kicked = on_notice(rule=comman_rule(GroupDecreaseNoticeEvent, sub_type="kick_me"))

@kicked.handle()
async def kicked_remind(bot: Bot, event: GroupDecreaseNoticeEvent):
    msg = f'被 {event.operator_id} 踢出群 {event.group_id}'
    logger.info(msg)
    for su in SUPERUSERS:
        await kicked.finish(msg)