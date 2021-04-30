from nonebot import MatcherGroup
from nonebot.adapters.cqhttp.event import GroupRequestEvent
from nonebot.permission import SUPERUSER
from nonebot.rule import ArgumentParser
from nonebot.adapters.cqhttp.exception import ActionFailed

from src.common import Bot, MessageEvent, T_State, SUPERUSERS
from src.common.rules import comman_rule


entry_and_exit = MatcherGroup()


entry_manager = entry_and_exit.on_request(rule=comman_rule(GroupRequestEvent, sub_type='invite'))


@entry_manager.handle()
async def entry_group(bot: Bot, event: GroupRequestEvent):
    if event.user_id in SUPERUSERS:
        await event.approve(bot)
    else:
        await bot.set_group_add_request(flag=event.flag, sub_type=event.sub_type, approve=False, reason='请联系维护组申请群授权')
        for sp in SUPERUSERS:
            await bot.send_private_msg(user_id=sp, message=f'收到来自 {event.user_id} 的群邀请 群号[{event.group_id}]\n加群申请flag: {event.flag}')


gid_parse = ArgumentParser()
gid_parse.add_argument('gid', type=int)


exit_manager = entry_and_exit.on_shell_command('退群', parser=gid_parse, permission=SUPERUSER)


@exit_manager.handle()
async def confirm_group(bot: Bot, event: MessageEvent, state: T_State):
    gid = state["args"].gid
    # try:
    #     groupinfo = await bot.get_group_info(group_id=gid)
    # except ActionFailed:
    #     await exit_manager.finish('获取群{gid}信息失败，请检查群号是否正确')
    g_ls = await bot.get_group_list()
    gid_ls = [g["group_id"] for g in g_ls]
    grpinfo_ls = '\n'.join([f'{i}.{g["group_name"]} | 群号[{g["group_id"]}]' for i, g in enumerate(g_ls)])  # 群文字列表
    if gid not in gid_ls:
        await exit_manager.finish(f'群不在列表中，当前已加入群的列表为：\n' + grpinfo_ls)
    else:
        state["gid"] = gid
        for g in g_ls:
            if g["group_id"] == gid:
                group_name = g["group_name"]
                break
        await exit_manager.send(f'获取到要退出的群信息：\n{group_name}\n是否确认退出: y/n')


@exit_manager.receive()
async def exit_group(bot: Bot, event: MessageEvent, state: T_State):
    if str(event.message).lower().strip() in ('y', '确认', '确定'):
        await bot.set_group_leave(group_id=state["gid"])
        await exit_manager.finish(f'好的，退出了群 {state["gid"]}')
    else:
        await exit_manager.finish(f'未收到明确的确认信息，忽略退群指令')