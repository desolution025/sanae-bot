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


chatbot = MatcherGroup(type='message')


set_prob = chatbot.on_command('聊天触发率', rule=sv_sw(plugin_name, plugin_usage)&comman_rule(GroupMessageEvent), priority=2)


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
        if prob > 0:
            msg = f'好的，{BOTNAME}最多只有{prob}%的几率插嘴啦~'
        else:
            msg = f'好的，{BOTNAME}不会插嘴啦~'
        await set_prob.finish(reply_header(event, msg))
    except IOError as err:
        logger.error(f'Record ai chat probability error: {err}')
        await set_prob.finish(reply_header(event, f'{BOTNAME}突然遭遇了不明袭击，没有记录下来，请尽快联系维护组修好我T_T'))


# 在这个里面的就不要触发了
BAN_EXPRESSION = ('姑姑请求场外支援呀',
                '这个…我真的听不懂',
                '尽管看不懂，但姑姑能够理解你此刻复杂的心情~',
                '哈哈哈，看不懂',
                '你好， 我是腾讯小龙女，请把你的问题告诉我吧',
                '不明白你的意思，我们还是聊聊今天的新闻吧',
                '先让我堵上耳朵，捂上眼睛')


def chat_checker(bot: Bot, event: MessageEvent, state: T_State):
    """闲聊触发率规则

    优先级规则内，to_me时必定触发
    否则真实触发率为 群设置聊天触发率 * 返回信息的可信度
    """
    msg = event.message.extract_plain_text()
    if not msg or len(msg) > 50:
        return False
    # 回复别人的对话不会触发
    for seg in event.message:
        if seg.type == 'at' and seg.data["qq"] not in (str(event.self_id), 'all') or event.reply and event.reply.sender.user_id != event.self_id:
            return False
    if event.message_type == 'group' and not event.is_tome():
        for name in BOTNAMES:
            if name in msg:
                person = '你' if msg.endswith(BOTNAME) else ''  # 名称在中间的时候替换成第二人称，名称在末尾时直接去掉
                state['q'] = msg.replace(name, person)
                return True  # 内容里有bot名字的话会默认触发
        gid = str(event.group_id)
        prob = prob_settings[gid] if gid in prob_settings else 0.05  # 默认触发率5%
        if random() > prob:
            return False
        else:
            ai_reply = ai_chat(msg)
            if ai_reply is None:
                logger.error(f'Failed to get tencent AI chat!') # 内部错误时返回的的是None
                return False
            else:
                reply, confidence = ai_chat(msg)
                if reply in BAN_EXPRESSION:
                    return False
            logger.debug(f'{msg} 获得触发率 {confidence:.5f}')
            if random() > confidence:
                return False
            else:
                state["reply"] = reply
    return True


chat = chatbot.on_message(rule=sv_sw(plugin_name, plugin_usage)&chat_checker, priority=4)


@chat.handle()
async def talk(bot: Bot, event: MessageEvent, state: T_State):
    q = state['q'] if 'q' in state else event.message.extract_plain_text()
    if "reply" not in state:
        reply, confidence = ai_chat(q)
    else:
        reply: str = state["reply"]

    if reply.startswith('呵呵'):  # 替掉开头的呵呵
        reply = reply.replace('呵呵', '呼呼')

    await chat.finish(reply.replace('腾讯', '幻想乡'))