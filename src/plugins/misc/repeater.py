from nonebot.plugin import on_notice
from src.common.rules import sv_sw


plugin_name = '复读机'
plugin_usage = '''复读机坏了，等修'''


repeater = on_notice(rule=sv_sw(plugin_name, plugin_usage, '其它'))