from pathlib import Path
from datetime import date, timedelta
from random import choice
from nonebot.plugin import on_message
from src.common import Bot, MessageEvent, logger
from src.common.rules import sv_sw, full_match
from src.utils import imgseg, DailyNumberLimiter
from .ballot import query_fortune, draw_fortune


plugin_name = '运势'
plugin_usage = """[今日运势] 没日一抽，运气好的话当天可能出门被撞到异世界当美少女"""


assets_folder = (Path(__file__).parent/'images'/'fortune')
sticks = [i for i in  assets_folder.glob('*.[jp][pn]*g')]


fortune = on_message(rule=sv_sw('运势')&full_match(('运势', '今日运势')), priority=2)


@fortune.handle()
async def check_fortune(bot: Bot, event: MessageEvent):
    name = event.sender.card if event.message_type == 'group' else event.sender.nickname
    dlmt = DailyNumberLimiter(event.user_id, func_name='运势', max_num=1)
    stick = query_fortune(event.user_id)
    if dlmt.check(close_conn=False) or not stick:
        stick = choice(sticks)
        draw_fortune(event.user_id, stick.name)
        dlmt.increase()
    else:
        stick = assets_folder/stick
    logger.debug(f'{event.user_id} got stick {stick.name}')
    await fortune.finish(f'{name}今日的运势是' + imgseg(stick), at_sender=True)