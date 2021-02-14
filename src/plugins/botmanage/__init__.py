from pathlib import Path
from nonebot import load_plugins
from nonebot.message import run_preprocessor
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event
from nonebot.typing import T_State
from nonebot.exception import IgnoredException
from .verify import Group_Blocker, User_Blocker


# 事件预处理规则，message类型的群聊内如果被阻塞中，非对bot使用的启动命令会忽略
@run_preprocessor
async def global_switch_filter(mathcer: Matcher, bot: Bot, event: Event, state:T_State):
    if event.get_type() == 'message' and event.message_type == 'group' and not Group_Blocker(event.group_id).check_block()\
        and not (event.get_message().extract_plain_text() in ('on', '启动', 'ON') and event.is_tome()):
        raise IgnoredException('该群已在全局关闭服务')
    if event.get_type() in ('message', 'notice', 'request') and not User_Blocker(event.user_id).check_block():
        raise IgnoredException('该用户在阻塞列表中')


# store all subplugins
manager_plugins = set()
# load sub plugins
manager_plugins |= load_plugins(
    str((Path(__file__).parent / "plugins").resolve()))