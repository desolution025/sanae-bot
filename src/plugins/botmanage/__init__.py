from pathlib import Path
from datetime import datetime,timedelta

from nonebot import load_plugins, on_shell_command
from nonebot.message import run_preprocessor
from nonebot.matcher import Matcher
from nonebot.rule import ArgumentParser
from nonebot.typing import T_State
from nonebot.permission import SUPERUSER
from nonebot.exception import IgnoredException
from nonebot_adapter_gocq.bot import Bot
from nonebot_adapter_gocq.event import Event, MessageEvent, NoticeEvent, PrivateMessageEvent, GroupIncreaseNoticeEvent, GroupDecreaseNoticeEvent, PrivateMessageSentEvent
from nonebot_adapter_gocq.permission import PRIVATE_FRIEND

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
    group_ls = await bot.get_group_list()
    gid_ls = [g["group_id"] for g in group_ls]
    if args.group in gid_ls:
        await bot.send_group_msg(group_id=args.group, message=f'已添加本群授权，到期时间：{(datetime.now() + timedelta(days=args.time)):%Y-%m-%d %H:%M:%S}')


# 事件预处理规则，群未被授权 或 群响应被关闭 且 对bot使用的启动命令以外 会忽略 自己加群或者自己被踢要排除在外
@run_preprocessor
async def global_switch_filter(mathcer: Matcher, bot: Bot, event: Event, state:T_State):
    if isinstance(event, (MessageEvent, NoticeEvent)) and hasattr(event, 'group_id') and\
        not (isinstance(event, GroupIncreaseNoticeEvent) and event.self_id == event.user_id or isinstance(event, GroupDecreaseNoticeEvent) and event.sub_type == 'kick_me') and\
        (not Enable_Group(event.group_id).check_enable() or not Group_Blocker(event.group_id).check_block() and\
        not (isinstance(event, MessageEvent) and event.get_message().extract_plain_text() in ('on', '启动', 'ON') and event.is_tome())):

        raise IgnoredException('该群已在全局关闭服务')

    if event.get_type() in ('message', 'notice', 'request') and not User_Blocker(event.user_id).check_block():
        raise IgnoredException('该用户在阻塞列表中')

    if isinstance(event, PrivateMessageEvent) and event.user_id == event.self_id:
        raise IgnoredException('由于当前版本gocq客户端的上报消息类型错误问题必须阻断的事件')
        # data = {}
        # for p in filter(lambda x: not (x.startswith('__') and x.endswith('__')), dir(event)):
        #     data[p] = getattr(event, p)
        # event = PrivateMessageSentEvent(**data)


# store all subplugins
manager_plugins = set()
# load sub plugins
manager_plugins |= load_plugins(
    str((Path(__file__).parent / "plugins").resolve()))