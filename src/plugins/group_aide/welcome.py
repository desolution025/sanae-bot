from pathlib import Path
import ujson as json

from nonebot import MatcherGroup
from nonebot_adapter_gocq.event import GroupIncreaseNoticeEvent

from src.common import Bot, GroupMessageEvent, T_State
from src.common.rules import sv_sw, comman_rule


plugin_name = ''
plugin_usage = ''


welcome_settings_file = Path(__file__)/"welcome_settings.json"


if not welcome_settings_file.exists():
    with welcome_settings_file.open('w', encoding='utf-8') as j:
        json.dump({}, j, ensure_ascii=False, escape_forward_slashes=False, indent=4)


with welcome_settings_file.open(encoding='utf-8') as j:
    welcome_settings = json.load(j)
"""
setting 结构：
{
    gid: {
        speech: [str, ...], 
        locked: bool
        },
    ...
}
"""


welcome = MatcherGroup(rule=sv_sw(plugin_name, plugin_usage, hierarchy='group_aid'))
speech_editor = welcome.on_command('设置welcome', rule=comman_rule(GroupMessageEvent), priority=2)
entry_welcome = welcome.on_request(rule=comman_rule(GroupIncreaseNoticeEvent))


@speech_editor.handle()
async def show_speech(bot: Bot, event: GroupMessageEvent, state: T_State):
    gid = str(event.group_id)
    if gid not in welcome_settings:
        wl_setting = {'speech': 'default speech', 'locked': False}
    else:
        wl_setting = welcome_settings[gid]
    speeches = '\n'.join([f'{i+1}.{speech}' for i, speech in enumerate(wl_setting['speech'])])
    await speech_editor.send('There is following speeches now:\n' + speeches + 'Select one operation: [add] [remove]')