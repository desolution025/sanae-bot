from random import random
import ujson as json
from pathlib import Path
from nonebot import MatcherGroup
from src.common import Bot, MessageEvent, T_State
from src.common.rules import sv_sw
from src.common import logger
from src.utils import reply_header
from .tccli_nlp import ai_chat


plugin_name = 'AI聊天'


configfile = Path(__file__).parent/'chat_prob.json'

if not configfile.exists():
    with configfile.open('w', encoding='utf-8') as j:
        json.dump({}, j, indent=4)
    
with configfile.open(encoding='utf-8') as j:
    prob_settings = json.load(j)


def record_settings(gid: str, prob: float):
    prob_settings[gid] = prob
    with configfile.open('w', encoding='utf-8') as j:
        json.dump(prob_settings, j, indent=4)


chatbot = MatcherGroup(type='message', rule=sv_sw('AI聊天'))


def chat_checker(bot: Bot, event: MessageEvent, state: T_State):
    """闲聊触发率规则

    优先级规则内，to_me时必定触发
    否则真实触发率为 群设置聊天触发率 * 返回信息的可信度
    """

    if event.message_type == 'group' and not event.is_tome():
        gid = str(event.group_id)
        prob = prob_settings[gid] if gid in prob_settings else 0.1
        if random() > prob:
            return False
        else:
            reply, confidence = ai_chat(event.message.extract_plain_text())
            logger.debug(f'{event.message.extract_plain_text()} 获得触发率 {confidence:.5f}')
            if random() > confidence:
                return False
            else:
                state["reply"] = reply
    return True
        

chat = chatbot.on_message(rule=chat_checker, priority=4)


@chat.handle()
async def talk(bot: Bot, event: MessageEvent, state: T_State):
    if "reply" not in state:
        reply, confidence = ai_chat(event.message.extract_plain_text())
    else:
        reply = state["reply"]

    await chat.finish(reply)