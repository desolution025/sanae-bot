from nonebot import on_command, get_loaded_plugins
from src.common import Bot, MessageEvent, BOTNAME, logger
from src.common.rules import group_func_off


_plugin_name = "使用帮助"


loaded_plugins = None


total_help = f"""
<Sanae-Bot使用说明>

[早苗 on|off] 控制{BOTNAME}在本群的全局开关（需群管理权限）
[开启|关闭] + <功能名> 控制单个功能开关（需群管理权限）
[签到] 领取每日低保
[查询等级] 查看当前等级""" """
——————功能列表——————
{sv_ls_}
———————————————————
发送使用"[使用帮助] <功能名>"查看功能详细说明
"""

helper = on_command('help', aliases={'帮助', '使用帮助', '使用说明'}, priority=2)


@helper.handle()
async def show_help(bot: Bot, event: MessageEvent):
    global loaded_plugins
    if loaded_plugins is None:
        loaded_plugins = [p for p in get_loaded_plugins() if hasattr(p.module, 'plugin_name')]
    if not event.message.extract_plain_text().strip():
        sv_names = list(map(lambda x: x.module.plugin_name, loaded_plugins))
        logger.debug(f'all_sv: {list(sv_names)}')
        if event.message_type == 'group':
            sv_on = filter(lambda x: x not in group_func_off[str(event.group_id)], sv_names)
            sv_off = filter(lambda x: x in group_func_off[str(event.group_id)], sv_names)
            # logger.debug(f'sv_on: {list(sv_on)}\nsv_off: {list(sv_off)}')
            sv_ls = "[已开启]\n" + '\n'.join(sv_on) + "\n[已关闭]\n" + '\n'.join(sv_off)
        else:
            sv_ls = '\n'.join(sv_names)
        await helper.finish(total_help.format(sv_ls_=sv_ls))

    # TODO: 单个功能的帮助

    

