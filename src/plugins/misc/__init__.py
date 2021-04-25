from pathlib import Path

from nonebot import on_command
from nonebot.adapters.cqhttp.message import Message
from nonebot.adapters.cqhttp.utils import unescape
from nonebot import load_plugins

from src.common import Bot, MessageEvent, T_State


echo = on_command('echo')


@echo.handle()
async def handle_receive(bot: Bot, event: MessageEvent, state: T_State):
    args = str(event.get_message()).strip()
    if args:
        state['msg'] = args

@echo.got('msg', prompt="Enter your input content: ")
async def got_message(bot: Bot, event: MessageEvent, state:T_State):
    msg = event.get_message()
    await echo.send(Message(unescape(str(msg))))


# store all subplugins
manager_plugins = set()
# load sub plugins
manager_plugins |= load_plugins(
    str((Path(__file__).parent).resolve()))