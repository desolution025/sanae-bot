from pathlib import Path
import ujson as json
from typing import Dict, List
from random import choice

from nonebot import MatcherGroup
from nonebot_adapter_gocq.event import GroupIncreaseNoticeEvent, GroupDecreaseNoticeEvent

from src.common import Bot, GroupMessageEvent, T_State, Message, logger
from src.common.rules import sv_sw, comman_rule


plugin_name = '入群退群提醒'
plugin_usage = ''


#———————————————————————————————入群提醒———————————————————————————————

welcome_name = '入群欢迎'
welcome_usage = """
入群仪式，支持图片，可设置多个欢迎语句，随机触发
[设置入群欢迎] 显示当前群聊欢迎语句，具体设置按照操作提示进行
""".strip()


welcome_settings_file = Path(__file__).parent/"welcome_settings.json"


if not welcome_settings_file.exists():
    with welcome_settings_file.open('w', encoding='utf-8') as j:
        json.dump({}, j, ensure_ascii=False, escape_forward_slashes=False, indent=4)


with welcome_settings_file.open(encoding='utf-8') as j:
    welcome_settings :Dict = json.load(j)
"""
setting 结构：
{
    gid(str): {
        approve: [str, ...],  (主动加群)
        invite: [str, ...],  (被邀请入群)
        locked: bool  (是否被锁定，决定群员是否可以修改邀请语句)
        },
    ...
}
"""

DEFAULT_SPEECH = {
            'approve': [
                '你已经是群主啦，快穿上女装参加登基大典吧！',
                '{name}加入了女装大家庭，大家快快穿上女装夹道欢迎吧！'
                ],
            # 'invite': [
            #     '欢迎{name}来到{admin}的女装殿堂，让{admin}亲自为您挑选合适的款式吧！',
            #     '{admin}邀请{name}给大家展示女装姐妹丼啦，欸欸~米娜桑不要脱裤子啊(＃°Д°)'
            #     ],
            'locked': False
            }  # 暂时没发现有条件能上报operator_id，所以invite就先不管了


def save_wl_settings():
    """保存群欢迎语句设置"""
    with welcome_settings_file.open('w', encoding='utf-8') as j:
        json.dump(welcome_settings, j, ensure_ascii=False, escape_forward_slashes=False, indent=4)


welcome = MatcherGroup()
welcome_sw = sv_sw(welcome_name, welcome_usage, hierarchy='群助手')

speech_editor = welcome.on_command('设置入群欢迎', rule=welcome_sw&comman_rule(GroupMessageEvent), priority=2)


@speech_editor.handle()
async def show_speech(bot: Bot, event: GroupMessageEvent, state: T_State):
    gid = str(event.group_id)
    if gid not in welcome_settings:
        wl_setting = DEFAULT_SPEECH
    else:
        wl_setting = welcome_settings[gid]
    ap_speeches = '\n'.join([f'{i+1}.{speech}' for i, speech in enumerate(wl_setting['approve'])])
    # in_speeches = '\n'.join([f'{i+1+len(wl_setting["approve"])}.{speech}' for i, speech in enumerate(wl_setting['invite'])])
    status = '已锁定' if wl_setting['locked'] else '未锁定'
    msg = '当前新人入群欢迎语句为：\n' + ap_speeches + '\n────────────\n可修改状态：' + status
    if wl_setting['locked'] and event.sender.role == 'member':
        await speech_editor.finish(Message(msg))
    else:
        # msg += '\n────────────\n使用以下命令修改通知语句(不带中括号)：\n[添加] 添加一个迎新语句(使用{name}字段可自动替换新人的昵称，参考默认欢迎语句)\n[添加邀请入群] 添加一个被邀请入群欢迎语句(除{name}之外可使用{admin}字段可自动替换邀请人的昵称，参考默认邀请语句)\n[删除+序号] 删除指定的语句\n[切换锁定] 更改锁定状态，锁定状态下群员不可修改欢迎语句'
        msg += '\n────────────\n使用以下命令修改通知语句(不带中括号)：\n[添加] 添加一个迎新语句(使用{name}字段可自动替换新人的昵称，参考默认欢迎语句)\n[删除+序号] 删除指定的语句\n[切换锁定] 更改锁定状态，锁定状态下群员不可修改欢迎语句'
        await speech_editor.send(Message(msg))


@speech_editor.receive()
async def edit_speech(bot: Bot, event: GroupMessageEvent, state: T_State):
    operation = event.raw_message
    gid = str(event.group_id)
    if gid not in welcome_settings:
        welcome_settings[gid] = DEFAULT_SPEECH
    settings = welcome_settings[gid]

    if operation.startswith('添加'):
        if len(settings['approve']) >= 5:
            await speech_editor.finish('最大支持存储5条迎新语句，请先删除不需要的语句')
        arg = operation[2:].strip()
        if arg:
            settings['approve'].append(arg)
            save_wl_settings()
            await speech_editor.finish('好的，已经添加一个迎新语句')
        else:
            # state['operation'] = 'add_approve'
            state['operation'] = 'add'
            await speech_editor.pause('请输入要添加的迎新语句(使用{name}字段可自动替换新人的昵称，参考默认欢迎语句)，输入[取消]退出当前操作')
    
    # elif operation.startswith('添加邀请入群'):
    #     if len(settings['invite']) >= 5:
    #         await speech_editor.finish('最大支持存储5条被邀请入群欢迎语句，请先删除不需要的语句')
    #     arg = operation[6:].strip()
    #     if arg:
    #         settings['invite'].append(arg)
    #         save_wl_settings()
    #         await speech_editor.finish('好的，已经添加一个被邀请入群欢迎语句')
    #     else:
    #         state['operation'] = 'add_invite'
    #         await speech_editor.pause('请输入要添加的被邀请入群欢迎语句，(使用{admin}字段可自动替换邀请人的昵称，参考默认邀请语句)，输入[取消]退出当前操作')

    elif operation.startswith('删除'):
        arg = operation[2:].strip()
        if arg:
            if arg.isdigit():
                index = int(arg)
                # if index > 0 and index <= len(settings['approve']) + len(settings['invite']):
                if index > 0 and index <= len(settings['approve']):
                    # if index <= len(settings['approve']):
                    #     del settings['approve'][index - 1]
                    # else:
                    #     index -= len(settings['approve'])
                    #     del settings['invite'][index - 1]
                    del settings['approve'][index - 1]
                    save_wl_settings()
                    await speech_editor.finish(f'已删除序号为{index}的迎新语句')
                else:
                    await speech_editor.finish('输入的参数不在列表内，请检查序号')
            else:
                await speech_editor.finish('只支持纯数字参数，请重新开启此对话进行操作')
        else:
            state['operation'] = 'delete'
            await speech_editor.pause('请输入需要删除的语句的序号，输入[取消]退出当前操作')

    elif operation.strip() == '切换锁定':
        settings['locked'] = not settings['locked']
        save_wl_settings()
        if settings['locked']:
            await speech_editor.finish('已锁定群欢迎语句')
        else:
            await speech_editor.finish('已解锁群欢迎语句，群员可随意修改语句')

    else:
        await speech_editor.finish('已退出编辑欢迎语句操作')


@speech_editor.handle()
async def wl_secondary_operation(bot: Bot, event: GroupMessageEvent, state: T_State):
    gid = str(event.group_id)
    if gid not in welcome_settings:
        welcome_settings[gid] = DEFAULT_SPEECH
    settings = welcome_settings[gid]
    # if state['operation'] == 'add_approve':
    if state['operation'] == 'add':
        settings['approve'].append(event.raw_message)
        msg = '好的，已经添加一个迎新语句'
    # elif state['operation'] == 'add_invite':
    #     settings['invite'].append(event.raw_message)
    #     msg = '好的，已经添加一个被邀请入群欢迎语句'
    elif state['operation'] == 'delete':
        if event.raw_message.isdigit():
            index = int(event.raw_message)
            # if index > 0 and index <= len(settings['approve']) + len(settings['invite']):
            if index > 0 and index <= len(settings['approve']):
                # if index <= len(settings['approve']):
                #     del settings['approve'][index - 1]
                #     msg = f'已删除序号为{index}的入群欢迎语句'
                # else:
                #     index -= len(settings['approve'])
                #     del settings['invite'][index - 1]
                #     msg = f'已删除序号为{index}的被邀请群欢迎语句'
                del settings['approve'][index - 1]
                msg = f'已删除序号为{index}的迎新语句'
            else:
                await speech_editor.finish('输入的参数不在列表内，请检查序号')
        else:
            await speech_editor.finish('只支持纯数字参数，请重新开启此对话进行操作')
    else:
        logger.error(f"Unkown session with operation: {state['operation']}")
        await speech_editor.finish('未知的对话进度，请联系维护组进行排查')
    save_wl_settings()
    await speech_editor.finish(msg)


#———————————————入群触发————————————————


def welcome_rule(bot: Bot, event: GroupIncreaseNoticeEvent, state: T_State):
    """排除自己加群的情况，排除加群语句被删除到没有了的情况"""
    if not isinstance(event, GroupIncreaseNoticeEvent):
        return False
    logger.debug(f'Group {event.group_id} increase Got!!')
    logger.debug(isinstance(event, GroupIncreaseNoticeEvent))
    if event.user_id == event.self_id:
        return False
    logger.debug('非自身加群')
    gid = str(event.group_id)
    if gid in welcome_settings:
        if event.sub_type == 'approve' and len(welcome_settings[gid]['approve']) == 0:
            # or event.sub_type == 'invite' and len(welcome_settings[gid]['invite']) == 0:
            return False
    return True


entry_welcome = welcome.on_notice(rule=welcome_sw&welcome_rule)


@entry_welcome.handle()
async def welcome_newcomers(bot: Bot, event: GroupIncreaseNoticeEvent):
    gid = str(event.group_id)
    if gid not in welcome_settings:
        welcome_settings[gid] = DEFAULT_SPEECH
    settings = welcome_settings[gid]
    userinfo = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
    name = userinfo['card'] or userinfo['nickname'] or str(event.user_id)
    # admininfo = await bot.get_group_member_info(group_id=event.group_id, user_id=event.operator_id)
    # admin = admininfo['card'] or admininfo['nickname'] or str(event.user_id)
    # msg = Message(choice(settings[event.sub_type]).format(name=name, admin=admin))
    msg = Message(choice(settings['approve']).format(name=name))
    await entry_welcome.finish(msg, at_sender=True)


#———————————————————————————————退群提醒———————————————————————————————


exitremind_name = '退群提醒'
exitremind_usage = """
退群提示，支持图片，可设置多个欢迎语句，随机触发
[设置退群提醒] 显示当前群聊退群提醒语句，具体设置按照操作提示进行
""".strip()


exitremind_settings_file = Path(__file__).parent/"exitremind_settings.json"


if not exitremind_settings_file.exists():
    with exitremind_settings_file.open('w', encoding='utf-8') as j:
        json.dump({}, j, ensure_ascii=False, escape_forward_slashes=False, indent=4)


with exitremind_settings_file.open(encoding='utf-8') as j:
    exitremind_settings :Dict = json.load(j)
"""
setting 结构：
{
    gid(str): {
        leave: [str, ...],  (主动退群)
        kick: [str, ...],  (成员被踢)
        locked: bool  (是否被锁定，决定群员是否可以修改退群语句)
        },
    ...
}
"""

DEFAULT_REMIND = {
            'leave': [
                '丑逼狗群主把{name}吓退群啦！'
                ],
            'kick': [
                '狗比管理{admin}为了掩盖自己援交的黑历史把{name}踢出群啦！'
                ],
            'locked': False
            }


def save_en_settings():
    """保存群退群提醒语句设置"""
    with exitremind_settings_file.open('w', encoding='utf-8') as j:
        json.dump(exitremind_settings, j, ensure_ascii=False, escape_forward_slashes=False, indent=4)


exitremind = MatcherGroup()
exitremind_sw = sv_sw(exitremind_name, exitremind_usage, hierarchy='群助手')

remind_editor = exitremind.on_command('设置退群提醒', rule=exitremind_sw&comman_rule(GroupMessageEvent), priority=2)


@remind_editor.handle()
async def show_remind(bot: Bot, event: GroupMessageEvent, state: T_State):
    gid = str(event.group_id)
    if gid not in exitremind_settings:
        en_setting = DEFAULT_REMIND
    else:
        en_setting = exitremind_settings[gid]
    lv_reminds = '\n'.join([f'{i+1}.{speech}' for i, speech in enumerate(en_setting['leave'])])
    kk_reminds = '\n'.join([f'{i+1+len(en_setting["leave"])}.{speech}' for i, speech in enumerate(en_setting['kick'])])
    status = '已锁定' if en_setting['locked'] else '未锁定'
    msg = '当前群内主动退群提醒语句为：\n' + lv_reminds + '\n────────────\n被管理踢出群聊提醒语句为：\n' + kk_reminds + '\n────────────\n可修改状态：' + status
    if en_setting['locked'] and event.sender.role == 'member':
        await remind_editor.finish(Message(msg))
    else:
        msg += '\n────────────\n使用以下命令修改通知语句(不带中括号)：\n[添加主动退群] 添加一个主动退群提醒语句(使用{name}字段可自动替换退群者的昵称，参考默认邀请语句)\n[添加管理踢人] 添加一个管理踢人提醒语句(除{name}之外可使用{admin}字段可自动替换执行的管理的昵称，参考默认踢人提醒语句)\n[删除+序号] 删除指定的语句\n[切换锁定] 更改锁定状态，锁定状态下群员不可修改退群提醒语句'
        await remind_editor.send(Message(msg))


@remind_editor.receive()
async def edit_remind(bot: Bot, event: GroupMessageEvent, state: T_State):
    operation = event.raw_message
    gid = str(event.group_id)
    if gid not in exitremind_settings:
        exitremind_settings[gid] = DEFAULT_SPEECH
    settings = exitremind_settings[gid]

    if operation.startswith('添加主动退群'):
        if len(settings['leave']) >= 5:
            await remind_editor.finish('最大支持存储5条主动退群提醒语句，请先删除不需要的语句')
        arg = operation[6:].strip()
        if arg:
            settings['leave'].append(arg)
            save_en_settings()
            await remind_editor.finish('好的，已经添加一个主动退群提醒语句')
        else:
            state['operation'] = 'add_leave'
            await remind_editor.pause('请输入要添加的主动退群提醒语句, 输入[取消]退出当前操作')
    
    elif operation.startswith('添加管理踢人'):
        if len(settings['kick']) >= 5:
            await remind_editor.finish('最大支持存储5条管理踢人提醒语句，请先删除不需要的语句')
        arg = operation[6:].strip()
        if arg:
            settings['kick'].append(arg)
            save_en_settings()
            await remind_editor.finish('好的，已经添加一个管理踢人提醒语句')
        else:
            state['operation'] = 'add_kick'
            await remind_editor.pause('请输入要添加的管理踢人提醒语句，(使用{admin}字段可自动替换执行的管理的昵称，参考默认踢人提醒语句)，输入[取消]退出当前操作')

    elif operation.startswith('删除'):
        arg = operation[2:].strip()
        if arg:
            if arg.isdigit():
                index = int(arg)
                if index > 0 and index <= len(settings['leave']) + len(settings['kick']):
                    if index <= len(settings['leave']):
                        del settings['leave'][index - 1]
                    else:
                        index -= len(settings['leave'])
                        del settings['kick'][index - 1]
                    save_en_settings()
                    await remind_editor.finish(f'已删除序号为{index}的提醒语句')
                else:
                    await remind_editor.finish('输入的参数不在列表内，请检查序号')
            else:
                await remind_editor.finish('只支持纯数字参数，请重新开启此对话进行操作')
        else:
            state['operation'] = 'delete'
            await remind_editor.pause('请输入需要删除的语句的序号，输入[取消]退出当前操作')

    elif operation.strip() == '切换锁定':
        settings['locked'] = not settings['locked']
        save_en_settings()
        if settings['locked']:
            await remind_editor.finish('已锁定退群提醒语句')
        else:
            await remind_editor.finish('已解锁退群提醒语句，群员可随意修改语句')

    else:
        await remind_editor.finish('已退出编辑退群提醒操作')


@remind_editor.handle()
async def en_secondary_operation(bot: Bot, event: GroupMessageEvent, state: T_State):
    logger.debug(f'Handle brach with {state["operation"]}')
    gid = str(event.group_id)
    if gid not in exitremind_settings:
        exitremind_settings[gid] = DEFAULT_REMIND
    settings = exitremind_settings[gid]
    if state['operation'] == 'add_leave':
        settings['leave'].append(event.raw_message)
        msg = '好的，已经添加一个主动退群提醒语句'
    elif state['operation'] == 'add_kick':
        settings['kick'].append(event.raw_message)
        msg = '好的，已经添加一个管理踢人提醒语句'
    elif state['operation'] == 'delete':
        if event.raw_message.isdigit():
            index = int(event.raw_message)
            if index > 0 and index <= len(settings['leave']) + len(settings['kick']):
                if index <= len(settings['leave']):
                    del settings['leave'][index - 1]
                    msg = f'已删除序号为{index}的退群提醒语句'
                else:
                    index -= len(settings['leave'])
                    del settings['kick'][index - 1]
                    msg = f'已删除序号为{index}的管理踢人提醒语句'
            else:
                await remind_editor.finish('输入的参数不在列表内，请检查序号')
        else:
            await remind_editor.finish('只支持纯数字参数，请重新开启此对话进行操作')
    else:
        logger.error(f"Unkown session with operation: {state['operation']}")
        await remind_editor.finish('未知的对话进度，请联系维护组进行排查')
    save_en_settings()
    await remind_editor.finish(msg)


#———————————————退群触发————————————————


def exitremind_rule(bot: Bot, event: GroupDecreaseNoticeEvent, state: T_State):
    """排除自己被踢出群的情况，排除退群语句被删除到没有了的情况"""
    if not isinstance(event, GroupDecreaseNoticeEvent):
        return False
    logger.debug(f'Group {event.group_id} decrease Got!!')
    logger.debug(isinstance(event, GroupDecreaseNoticeEvent))
    if event.sub_type == 'kick_me':
        return False
    gid = str(event.group_id)
    if gid in exitremind_settings:
        if event.sub_type == 'leave' and len(exitremind_settings[gid]['leave']) == 0 \
            or event.sub_type == 'kick' and len(exitremind_settings[gid]['kick']) == 0:
            return False
    return True


entry_exitremind = exitremind.on_notice(rule=exitremind_sw&exitremind_rule)


@entry_exitremind.handle()
async def member_exit_remind(bot: Bot, event: GroupDecreaseNoticeEvent):
    gid = str(event.group_id)
    if gid not in exitremind_settings:
        exitremind_settings[gid] = DEFAULT_REMIND
    settings = exitremind_settings[gid]
    userinfo = await bot.get_stranger_info(user_id=event.user_id)
    name = userinfo['nickname'] or str(event.user_id)
    if event.user_id != event.operator_id:
        admininfo = await bot.get_group_member_info(group_id=event.group_id, user_id=event.operator_id)
        admin = admininfo['card'] or admininfo['nickname'] or str(event.user_id)
    else:
        admin = name
    msg = Message(choice(settings[event.sub_type]).format(name=name, admin=admin))
    await entry_exitremind.finish(msg)