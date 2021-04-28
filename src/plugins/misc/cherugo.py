"""切噜语（ちぇる語, Language Cheru）转换

定义:
    W_cheru = '切' ^ `CHERU_SET`+
    切噜词均以'切'开头，可用字符集为`CHERU_SET`

    L_cheru = {W_cheru ∪ `\\W`}*
    切噜语由切噜词与标点符号连接而成
"""


import re
from itertools import zip_longest

from nonebot import MatcherGroup
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent

from src.common.rules import sv_sw
from src.utils import reply_header


plugin_name = '切噜语转换'


plugin_usage = '[切噜一下 随意文字] 转化为切噜语\n发送<切噜语> 转化为人类语言'


CHERU_SET = '切卟叮咧哔唎啪啰啵嘭噜噼巴拉蹦铃'
CHERU_DIC = {c: i for i, c in enumerate(CHERU_SET)}
ENCODING = 'gb18030'
rex_split = re.compile(r'\b', re.U)
rex_word = re.compile(r'^\w+$', re.U)
rex_cheru_word: re.Pattern = re.compile(rf'切[{CHERU_SET}]+', re.U)


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def word2cheru(w: str) -> str:
    c = ['切']
    for b in w.encode(ENCODING):
        c.append(CHERU_SET[b & 0xf])
        c.append(CHERU_SET[(b >> 4) & 0xf])
    return ''.join(c)


def cheru2word(c: str) -> str:
    if not c[0] == '切' or len(c) < 2:
        return c
    b = []
    for b1, b2 in grouper(c[1:], 2, '切'):
        x = CHERU_DIC.get(b2, 0)
        x = x << 4 | CHERU_DIC.get(b1, 0)
        b.append(x)
    return bytes(b).decode(ENCODING, 'replace')


def str2cheru(s: str) -> str:
    c = []
    for w in rex_split.split(s):
        if rex_word.search(w):
            w = word2cheru(w)
        c.append(w)
    return ''.join(c)


def cheru2str(c: str) -> str:
    return rex_cheru_word.sub(lambda w: cheru2word(w.group()), c)


cherugo = MatcherGroup(type='message', rule=sv_sw(plugin_name, usage=plugin_usage, hierarchy='其它'))


tocherugo = cherugo.on_startswith('切噜一下')


@tocherugo.handle()
async def cherulize(bot: Bot, event: MessageEvent):
    s = event.get_plaintext()
    if len(s) > 500:
        await tocherugo.finish(reply_header(event, '切、切噜太长切不动勒切噜噜...'))
    await tocherugo.finish(reply_header(event, '切噜～♪' + str2cheru(s)))


fromcherugo = cherugo.on_startswith('切噜～♪')


@fromcherugo.handle()
async def decherulize(bot: Bot, event: MessageEvent):
    s = event.get_plaintext()
    if len(s) > 1501:
        await fromcherugo.finish(reply_header(event, '切、切噜太长切不动勒切噜噜...'))
    msg = '的切噜噜是：\n' + cheru2str(s)
    await fromcherugo.finish(reply_header(event, msg))