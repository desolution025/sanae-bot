from nonebot import on_command
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.exception import CQHTTPAdapterException
from src.common import Bot, MessageEvent, T_State, logger, CANCEL_EXPRESSION


plugin_name = '群广播'


broadcast = on_command('broadcast', aliases={'bc', '广播', '通知群'}, permission=SUPERUSER)


@broadcast.handle()
async def first_receive(bot: Bot, event: MessageEvent, state: T_State):
    msg = event.message
    if msg:
        state["msg"] = msg


@broadcast.got('msg', prompt='输入需要发送的消息')
async def point_groups(bot: Bot, event: MessageEvent, state: T_State):
    if 'msg' not in state:
        state['msg'] = event.message

    g_ls = await bot.get_group_list()
    gid_ls = [g["group_id"] for g in g_ls]  # gid列表，通过列表索引指定群号
    grpinfo_ls = '\n'.join([f'{i}.{g["group_name"]} | 群号[{g["group_id"]}]' for i, g in enumerate(g_ls)])  # 群文字列表

    state["gid_ls"] = gid_ls
    await broadcast.send(f'选择要发送的群(逗号分隔):\n{grpinfo_ls}\n输入[退出]取消发送')


@broadcast.receive()
async def send_notice(bot: Bot, event: MessageEvent, state: T_State):
    args = event.message.extract_plain_text()
    if args in CANCEL_EXPRESSION:
        await broadcast.finish('已取消发送广播')
    if not args:
        await broadcast.reject('输入不能为空，请重新输入，输入[退出]取消发送')
    grps = args.replace('，', ',').split(',')
    gid_ls = state["gid_ls"]
    target_grps = []
    for g in grps:
        if not g.strip().isdigit():
            await broadcast.reject('非数字参数，请重新输入，输入[退出]取消发送')
            break
        gid = int(g.strip())
        if gid < 0 or gid > len(gid_ls):
            await broadcast.reject('序号超出范围，请重新输入，输入[退出]取消发送')
            break
        target_grps.append(gid)
    else:
        try:
            for i in target_grps:
                await bot.send_group_msg(group_id=gid_ls[i], message=state["msg"])
        except CQHTTPAdapterException as err:
            logger.error(f'Faild to send broadcast with error: {err}')
            await broadcast.finish(f'广播投递失败')

    await broadcast.finish(f'已将广播发送给{len(target_grps)}个群')