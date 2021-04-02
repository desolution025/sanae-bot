import re
from nonebot import MatcherGroup
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from src.common.rules import sv_sw
from .corpus import query


qanda = MatcherGroup(type='message', rule=sv_sw('问答对话'), priority=3)


reply = qanda.on_message()


@reply.handle()
async def reply_(bot: Bot, event: MessageEvent):
    question = event.get_message()
    print(f'plaintext|{event.get_plaintext()}')
    answer = query(str(question))
    if answer:
        await reply.finish(answer)
