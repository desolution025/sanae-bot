from nonebot import on_command
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event


echo = on_command('echo')


@echo.handle()
async def handle_receive(bot: Bot, event: Event, state: T_State):
    args = str(event.get_message()).strip()
    if args:
        state['msg'] = args

@echo.got('msg', prompt="Enter your input content: ")
async def got_message(bot: Bot, event: Event, state:T_State):
    msg = event.get_message()
    # print('unescape: ', msg, type(msg))
    await echo.send(msg)