from random import random
import ujson as json
from pathlib import Path

from nonebot import MatcherGroup

from src.common import Bot, MessageEvent, GroupMessageEvent, T_State, logger, BOTNAME, BOTNAMES
from src.common.rules import sv_sw, comman_rule
from src.utils import reply_header
from .tccli_nlp import ai_chat


plugin_name = 'AI聊天'
plugin_usage = """
﹟ 会在聊天中随机插嘴
﹟ 使用"聊天触发率 <0-50的数字>"可设置触发回复的最大百分比概率
﹟ 实际概率会根据是否能识别对话进一步下调
﹟ 默认为5%，建议不要设置过高
""".strip()


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


chatbot = MatcherGroup(type='message', rule=sv_sw(plugin_name, plugin_usage))


set_prob = chatbot.on_command('聊天触发率', rule=comman_rule(GroupMessageEvent), priority=2)


@set_prob.handle()
async def recieve_arg(bot: Bot, event: GroupMessageEvent, state: T_State):
    arg = event.message.extract_plain_text().strip()
    if arg:
        state['prob'] = arg


@set_prob.got("prob", prompt='请输入聊天触发率，范围0-50，输入[退出]取消设置触发率')
async def prob_handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    prob = state["prob"] if "prob" in state else event.message.extract_plain_text().strip()
    if not prob.isdigit():
        await set_prob.finish(reply_header(event, '仅支持数字参数~'))
    prob = int(prob)
    if prob < 0 or prob > 50:
        await set_prob.finish(reply_header(event, '范围错误，聊天触发率仅支持设置为0-50内'))
    try:
        record_settings(str(event.group_id), prob / 100)
        await set_prob.finish(reply_header(event, f'好的，{BOTNAME}最多只有{prob}%的几率插嘴啦~'))
    except Exception as err:
        logger.error(f'Record ai chat probability error: {err}')
        await set_prob.finish(reply_header(event, f'{BOTNAME}突然遭遇了不明袭击，没有记录下来，请尽快联系维护组修好我T_T'))


def chat_checker(bot: Bot, event: MessageEvent, state: T_State):
    """闲聊触发率规则

    优先级规则内，to_me时必定触发
    否则真实触发率为 群设置聊天触发率 * 返回信息的可信度
    """
    msg = event.message.extract_plain_text()
    if event.message_type == 'group' and not event.is_tome():
        for name in BOTNAMES:
            if name in msg:
                state['q'] = msg.replace(name, '你')
                return True  # 内容里有bot名字的话会默认触发
        gid = str(event.group_id)
        prob = prob_settings[gid] if gid in prob_settings else 0.1
        if random() > prob:
            return False
        else:
            reply, confidence = ai_chat(msg)
            logger.debug(f'{msg} 获得触发率 {confidence:.5f}')
            if random() > confidence:
                return False
            else:
                state["reply"] = reply
    return True
        

chat = chatbot.on_message(rule=chat_checker, priority=4)


@chat.handle()
async def talk(bot: Bot, event: MessageEvent, state: T_State):
    q = state['q'] if 'q' in state else event.message.extract_plain_text()
    if "reply" not in state:
        reply, confidence = ai_chat(q)
    else:
        reply = state["reply"]

    await chat.finish(reply)