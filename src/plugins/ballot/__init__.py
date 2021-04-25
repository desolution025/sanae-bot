from pathlib import Path
from random import choice
from nonebot import on_command
from src.common import Bot, MessageEvent
from src.common.rules import sv_sw


plugin_name = '运势'


sticks = [i for i in  (Path(__file__).parent/'images'/'fortune').glob('*.{jp}{pn}*g')]


fortune = on_command('运势', aliases={'今日运势'}, rule=sv_sw('运势'), priority=2)


# @fortune.handle()
# async def check_fortune(bot: Bot, event: MessageEvent):
#     if not str(event.message).strip():
#         dlmt = DailyNumberLimiter(event.user_id, '运势', 1)
#         if dlmt.check(close_conn=False):

# TODO: 用sqlite写个本地数据库吧