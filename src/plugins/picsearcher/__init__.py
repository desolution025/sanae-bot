# -*- coding: utf-8 -*-
import traceback
from typing import Dict

from aiohttp.client_exceptions import ClientError
from nonebot import on_command, MatcherGroup
from nonebot.adapters.cqhttp.exception import ActionFailed

from src.common import MessageSegment, logger, Bot, MessageEvent, T_State, GroupMessageEvent, Message
from src.common.rules import sv_sw, comman_rule
from src.utils import reply_header

from .ex import get_des as get_des_ex
from .iqdb import get_des as get_des_iqdb
from .saucenao import get_des as get_des_sau
from .ascii2d import get_des as get_des_asc
from .trace import get_des as get_des_trace
from .yandex import get_des as get_des_yandex


plugin_name = '搜图'
plugin_usage = """
原作者@synodriver
有些引擎挂掉了所以先精简到现在这样
如果有恢复的还会添加搜索模式
———————
[搜图 图片]从SauceNao和ascii2d搜图源
[上一张是什么] [搜上一张图]可以直接搜索刚刚发的图是啥
""".strip()


async def get_des(url: str, mode: str):
    """
    :param url: 图片链接
    :param mode: 图源
    :return:
    """
    if mode == "iqdb":
        async for msg in get_des_iqdb(url):
            yield msg
    elif mode == "ex":
        async for msg in get_des_ex(url):
            yield msg
    elif mode == "trace":
        async for msg in get_des_trace(url):
            yield msg
    elif mode == "yandex":
        async for msg in get_des_yandex(url):
            yield msg
    elif mode.startswith("asc"):
        async for msg in get_des_asc(url):
            yield msg
    else:
        async for msg in get_des_sau(url):
            yield msg


setu = on_command("搜图", aliases={"search"}, rule=sv_sw('搜图', plugin_usage), priority=2)


@setu.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    msg = event.message
    if msg:
        state["setu"] = msg


@setu.got("setu", prompt="图呢？")
async def get_setu(bot: Bot, event: MessageEvent, state: T_State):
    msg: Message = Message(state["setu"])
    try:
        for seg in msg:
            if seg.type == "image":
                url = seg.data["url"]  # 图片链接
                break
        else:
            await setu.finish(reply_header(event, "这也不是图啊!"))

        await bot.send(event=event, message="让我搜一搜...")
        result = MessageSegment.text('————>SauceNao<————')
        async for msg in get_des(url, 'sau'):
            if not msg:
                await setu.send('未从saucenao检索到高相似度图片，将运行ascii2d检索')
                break
            result += msg + '────────────\n'
        else:
            result = Message(str(result).rstrip('────────────\n'))
            await setu.finish(result)

        result = MessageSegment.text('————>ascii2d<————')
        async for msg in get_des(url, 'ascii2d'):
            if not msg:
                await setu.finish('未从ascii2d检索到高相似度图片，请等待加入更多检索方式')
                break
            result += msg + '────────────\n'
        else:
            result = Message(str(result).rstrip('────────────\n'))
            await setu.finish(result)

    except (IndexError, ClientError):
        logger.exception(traceback.format_exc())
        await setu.finish("遇到未知打击，中断了搜索")
    except ActionFailed as e:
        logger.error(f'Send result failed: {e}')
        await setu.finish('虽然搜到了，但是发送结果途中遭遇拦截，可稍后再试一试')


pic_map: Dict[str, str] = {}  # 保存这个群的其阿金一张色图 {"123456":http://xxx"}


async def check_pic(bot: Bot, event: MessageEvent, state: T_State) -> bool:
    for msg in event.message:
        if msg.type == "image":
            url: str = msg.data["url"]
            state["url"] = url
            return True
    return False


easy_pick = MatcherGroup(type='message', rule=sv_sw('搜图')&comman_rule(GroupMessageEvent)&check_pic, priority=2)


notice_pic =easy_pick.on_message()


@notice_pic.handle()
async def handle_pic(bot: Bot, event: GroupMessageEvent, state: T_State):
    try:
        group_id: str = str(event.group_id)
        pic_map.update({group_id: state["url"]})
    except AttributeError:
        pass


previous = easy_pick.on_command("上一张图是什么", aliases={"搜上一张图"})


@previous.handle()
async def handle_previous(bot: Bot, event: GroupMessageEvent, state: T_State):
    await bot.send(event=event, message="让我看看这个图")
    try:
        url: str = pic_map[str(event.group_id)]
        result = MessageSegment.text('————>SauceNao<————')
        async for msg in get_des(url, "nao"):
            if not msg:
                await previous.finish('没有搜到的说~')
            result += msg + '────────────\n'
        result = Message(str(result).rstrip('────────────\n'))
        await previous.send(reply_header(event, msg))
    except (IndexError, ClientError):
        logger.exception(traceback.format_exc())
        await previous.finish("啊，搜索中遇到了不明错误O_O")
    except KeyError:
        await previous.finish(reply_header(event, "没有图啊QAQ"))
    except ActionFailed:
        await previous.finish('虽然搜到了，但是发送结果途中遭遇拦截，可稍后再试一试')
