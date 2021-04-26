from nonebot import on_command, get_loaded_plugins
from src.common import Bot, MessageEvent, BOTNAME, logger
from src.common.rules import group_func_off
from src.utils import reply_header


_plugin_name = "使用帮助"


loaded_plugins = None
helper_dict = None


total_help = f"""
<Sanae-Bot使用说明>

[早苗 on|off] 控制{BOTNAME}在本群的全局开关（需群管理权限）
[开启|关闭] + <功能名> 控制单个功能开关（需群管理权限）
[签到] 领取每日低保
[查询等级] 查看当前等级""" """
—————功能列表—————
{sv_ls_}
——————————————
发送"使用帮助 <功能名>"查看功能详细说明
//**隐藏功能请自行探索**//
""".strip()


helper = on_command('help', aliases={'帮助', '使用帮助', '使用说明'}, priority=1)


@helper.handle()
async def show_help(bot: Bot, event: MessageEvent):
    global loaded_plugins
    if loaded_plugins is None:
        loaded_plugins = [p for p in get_loaded_plugins() if hasattr(p.module, 'plugin_name')]
    sv_names = list(map(lambda x: x.module.plugin_name, loaded_plugins))
    # 总帮助说明
    if not event.message.extract_plain_text().strip():
        logger.debug(f'all_sv: {list(sv_names)}')
        if event.message_type == 'group':
            sv_on = list(filter(lambda x: x not in group_func_off[str(event.group_id)], sv_names))
            sv_off = list(filter(lambda x: x in group_func_off[str(event.group_id)], sv_names))
            # logger.debug(f'sv_on: {list(sv_on)}\nsv_off: {list(sv_off)}')
            sv_ls = ''
            if sv_on:
                sv_ls += "[已开启]\n" + '\n'.join(map(lambda x: f'-{x}-', sv_on))
            if sv_off:
                if sv_on:
                    sv_ls += "\n"
                sv_ls += "[已关闭]\n" + '\n'.join(map(lambda x: f'-{x}-', sv_off))
        else:
            sv_ls = '\n'.join(sv_names)
        await helper.finish(total_help.format(sv_ls_=sv_ls))
    
    # 单个功能说明
    global helper_dict
    if helper_dict is None:
        helper_dict = {}
        for p in loaded_plugins:
            helper_dict[p.module.plugin_name] = p.module.plugin_usage if hasattr(p.module, 'plugin_usage') else '此功能没有描述'

    name = event.message.extract_plain_text().strip()
    if name not in helper_dict:
        await helper.finish(reply_header(f'没有找到名字为<{name}>的功能'))
    else:
        await helper.finish(f">——<{name}>——<\n{helper_dict[name]}")