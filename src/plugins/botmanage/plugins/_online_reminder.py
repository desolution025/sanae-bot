from nonebot import on_metaevent
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import LifecycleMetaEvent
from nonebot.typing import T_State
from nonebot import get_loaded_plugins
from src.common.easy_setting import SUPERUSERS


plugin_name = '上线提醒'


# 上线规则
async def online_rule(bot: Bot, event: LifecycleMetaEvent, state: T_State) -> bool:
    if isinstance(event, LifecycleMetaEvent) and event.sub_type == "connect":
        return True


online = on_metaevent(rule=online_rule)

@online.handle()
async def online_remind(bot: Bot):
    plugins = get_loaded_plugins()
    msg = 'online desu\n当前加载的插件：\n' + '\n'.join(map(lambda x: x.module.plugin_name, filter(lambda obj: hasattr(obj.module, 'plugin_name'), plugins)))

    for sps in SUPERUSERS:
        await bot.send_private_msg(user_id=sps, message=msg)