from pathlib import Path
from datetime import datetime,timedelta

from nonebot import load_plugins, on_shell_command
from nonebot.message import run_preprocessor
from nonebot.matcher import Matcher
from nonebot.rule import ArgumentParser
from nonebot.exception import IgnoredException
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event, PrivateMessageEvent
from nonebot.typing import T_State
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.permission import PRIVATE_FRIEND

from src.common.verify import Group_Blocker, User_Blocker, Enable_Group
from src.common import logger


parser = ArgumentParser()
parser.add_argument("-g", "--group", type=int)
parser.add_argument("-t", "--time", type=int)


warrant = on_shell_command('授权', parser=parser, permission=SUPERUSER|PRIVATE_FRIEND)


@warrant.handle()
async def authorize(bot: Bot, event: PrivateMessageEvent, state: T_State):
    args = state["args"]
    group_checker = Enable_Group(args.group)
    if group_checker.check_enable():
        group_checker.renewal(args.time)
        logger.success(f'群 {args.group} 续期 {args.time}天')
    else:
        logger.success(f'授权群 {args.group} {args.time}天，到期时间：{(datetime.now() + timedelta(days=args.time)):%Y-%m-%d %H:%M:%S}')
        group_checker.approve(args.time)


# 事件预处理规则，message类型的群聊内如果被阻塞中，非对bot使用的启动命令会忽略
@run_preprocessor
async def global_switch_filter(mathcer: Matcher, bot: Bot, event: Event, state:T_State):
    if hasattr(event, 'group_id') and not Enable_Group(event.group_id).check_enable() and not Group_Blocker(event.group_id).check_block()\
        and not (event.get_message().extract_plain_text() in ('on', '启动', 'ON') and event.is_tome()):
        raise IgnoredException('该群已在全局关闭服务')
    if event.get_type() in ('message', 'notice', 'request') and not User_Blocker(event.user_id).check_block():
        raise IgnoredException('该用户在阻塞列表中')


# store all subplugins
manager_plugins = set()
# load sub plugins
manager_plugins |= load_plugins(
    str((Path(__file__).parent / "plugins").resolve()))