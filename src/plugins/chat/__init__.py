from pathlib import Path
import re
from random import choice, randint
from emoji import emojize, demojize
from nonebot import MatcherGroup
from nonebot.adapters.cqhttp.message import Message
from src.common import Bot, MessageEvent, T_State
from src.common.rules import sv_sw
from src.common.log import logger
from .corpus import query, plus_one


plugin_name = '问答对话'


CORPUS_IMAGES_PATH = Path(r'.\res')/'images'/'corpus_images'


def msg2str(message: Message) -> str:
    """把Message转换成可供数据库插入和查询用的字符串

    对纯文本对emoji去转义，对image去除data中的url参数

    Args:
        message (Message): 可由event.message或event.get_message()获得

    Returns:
        str: 转换后的字符串
    """
    strcq = ''
    for seg in message:
        if seg.type == 'text':
            strcq += demojize(str(seg))
        elif seg.type == 'image':
            strcq += f'[CQ:image,file={seg.data["file"]}]'
        else:
            strcq += str(seg)
    return strcq


def msglize(msg: str, name: str="{name}") -> Message:
    """解析数据库answer时调用，把返回消息中的{res_path}替换为真实资源路径, 把{name}换成昵称并去转义emoji

    Args:
        msg (str): 数据库中的answer
        name (str, optional): 要替换{name}字段的字符，通常为event.sender.card|nickname. Defaults to "{name}".

    Returns:
        Message: 解析后自动转换Message
    """
    if '[CQ:image,' in msg or "{name}" in msg:
        msg = msg.format(res_path=CORPUS_IMAGES_PATH, name=name)
    return Message(emojize(msg))  # 由于nb2使用array上报数据所以要实例化为Message可直接转化旧版字符串数据


qanda = MatcherGroup(type='message', rule=sv_sw('问答对话'), priority=3)


def reply_checker(bot: Bot, event: MessageEvent, state: T_State) -> bool:
    """问答对话触发规则"""
    q = msg2str(event.message)
    gid = event.group_id if event.message_type == 'group' else 0
    result = query(q, gid)
    if not result:
        return False
    sid, answer, prob = choice(result)
    if event.to_me or randint(0, 100) < prob:
        if event.message_type == 'group':
            name = event.sender.card or event.sender.nickname or event.get_user_id()
        else:
            name = event.sender.nickname or event.get_user_id()
        state['answer'] = msglize(answer, name)
        state['sid'] = sid
        return True
    else:
        return False
    #—————————————测试成功后使用上面那个——————————
    # gen_num = randint(0, 100)
    # if event.to_me:
    #     logger.debug('to_me, 直接匹配')
    #     state['answer'] = emojize(answer)
    #     return True
    # elif gen_num < prob:
    #     logger.debug(f'匹配成功：q: {q}, prob: {prob}, 随机到: {gen_num}, 返回a: {answer}')
    #     state['answer'] = emojize(answer)
    #     return True
    # else:
    #     logger.debug(f'匹配失败：q: {q}, prob: {prob}, 随机到: {gen_num}, 返回a: {answer}')
    #     return False     


reply = qanda.on_message(rule=reply_checker)


@reply.handle()
async def reply_(bot: Bot, event: MessageEvent, state: T_State):
    plus_one(state['sid'])
    await reply.finish(state['answer'])