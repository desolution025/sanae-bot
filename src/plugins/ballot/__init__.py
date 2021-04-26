from pathlib import Path
from datetime import date, timedelta
from random import choice
from nonebot import on_command
from src.common import Bot, MessageEvent, logger
from src.common.rules import sv_sw
from src.utils import imgseg
from .ballot import query_fortune, draw_fortune


plugin_name = '运势'
plugin_usage = """[今日运势] 没日一抽，运气好的话当天可能出门被撞到异世界当美少女"""


assets_folder = (Path(__file__).parent/'images'/'fortune')
sticks = [i for i in  assets_folder.glob('*.{jp}{pn}*g')]


fortune = on_command('运势', aliases={'今日运势'}, rule=sv_sw('运势'), priority=2)


@fortune.handle()
async def check_fortune(bot: Bot, event: MessageEvent):
    if not str(event.message).strip():
        name = event.sender.card if event.message_type == 'group' else event.sender.nickname
        stick, lot_day = query_fortune(event.user_id)
        if lot_day < date.today():
            stick = choice(sticks)
        else:
            stick = assets_folder/stick
        logger.debug(f'{event.user_id} got stick {stick}')
        await fortune.finish(f'{name}今日的运势是' + imgseg(stick), at_sender=True)