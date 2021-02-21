from nonebot import on_notice
from nonebot.rule import Rule
from nonebot.adapters.cqhttp.event import PokeNotifyEvent
from src.common.rules import sv_sw, comman_rule


pokeme = on_notice(rule=Rule(comman_rule(PokeNotifyEvent)) &sv_sw('戳我'))

@pokeme.handle()
async def poke_me(bot, event: PokeNotifyEvent):
    await pokeme.finish(f'{event.user_id}戳了戳{event.target_id}')