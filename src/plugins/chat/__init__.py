from pathlib import Path
from typing import Optional
import re
from urllib.request import urlretrieve
from random import choice, randint
from emoji import emojize, demojize
from cn2an import cn2an
from nonebot import MatcherGroup
from nonebot.adapters.cqhttp.message import Message
from src.common import Bot, MessageEvent, GroupMessageEvent, PrivateMessageEvent, T_State, CANCEL_EXPRESSION
from src.common.rules import sv_sw
from src.common.log import logger
from src.common.levelsystem import UserLevel
from src.utils import reply_header, cgauss
from .corpus import query, plus_one, insert


plugin_name = '问答对话'


CORPUS_IMAGES_PATH = Path(r'.\res')/'images'/'corpus_images'


def localize(url: str, filename: str, failed_times: int=0) -> Optional[str]:
    """本地化图片存储在语料库图片文件夹

    Args:
        url (str): 要下载的url
        filename (str): 下载后存储的文件名称
        failed_times (int, optional): 初始失败次数. Defaults to 0.

    Returns:
        Optional[str]: 成功下载会返回下载后的文件储存路径，否则返回None
    """

    fp = CORPUS_IMAGES_PATH/filename
    if fp.exists():
        logger.debug(f'File [{filename}] has localized with {fp}')
        return fp
    try:
        urlretrieve(url, fp)
        logger.info(f'Localize image [{filename}] with path: {fp}')
        return fp
    except Exception as err:
        failed_times += 1
        logger.warning(f'Download file [{url}] error {failed_times} times: {err}')
        if failed_times < 6:
            return localize(url, filename, failed_times=failed_times)
        else:
            logger.error(f'Can not download file [{url}] with filename[{fp}]: {err}')
            return None


async def msg2str(message: Message, *, localize_: bool=False, bot: Optional[Bot]=None) -> str:
    """把Message转换成可供数据库插入和查询用的字符串

    对纯文本对emoji去转义，对image去除data中的url参数

    Args:
        message (Message): 可由event.message或event.get_message()获得
        localize_ (bool): 是否要本地化，本地化后file字段加入的是file:///...形式的本地文件格式，一般用在插入数据库中answer中

    Returns:
        str: 转换后的字符串
    """

    strcq = ''
    for seg in message:
        if seg.type == 'text':
            strcq += demojize(str(seg))
        elif seg.type == 'image':
            if not localize_:
                strcq += f'[CQ:image,file={seg.data["file"]}]'
            else:
                fileinfo = await bot.get_image(file=seg.data["file"])
                filename = re.sub(r'[\{\}-]', '', fileinfo["filename"]).lower()  # 返回filename字段是{xxx-xxx-xxx...}.jpg的形式，去掉中括号和横杠
                fp = localize(seg.data["url"], filename)
                if not fp:
                    return None
                strcq += f'[CQ:image,file={filename}]'
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


qanda = MatcherGroup(type='message', rule=sv_sw('问答对话'))


async def reply_checker(bot: Bot, event: MessageEvent, state: T_State) -> bool:
    """问答对话触发规则"""
    q = await msg2str(Message(event.raw_message))  # 仅仅使用message会去掉呼唤bot昵称的原文本，造成问句中有bot昵称时逻辑混乱
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


reply = qanda.on_message(rule=reply_checker, priority=3)


@reply.handle()
async def reply_(bot: Bot, event: MessageEvent, state: T_State):
    gid = event.group_id if event.message_type == 'group' else 0
    plus_one(state['sid'], gid)
    await reply.finish(state['answer'])


learn = qanda.on_command('学习', aliases={'学习对话', '群内学习', '私聊学习', '偷偷学习'})


@learn.handle()
async def first_receive(bot: Bot, event: MessageEvent, state: T_State):
    command = state["_prefix"]["raw_command"]
    if command == '群内学习':
        if isinstance(event, GroupMessageEvent):
            state["public"] = 0
        else:
            await learn.finish('[群内学习]只适用于在群中对话哦，公开性对话学习请使用[学习对话]，私聊内保密对话学习命令为[私聊学习]')
    elif command in ('私聊学习', '偷偷学习'):
        if isinstance(event, PrivateMessageEvent):
            state["public"] = 0
        else:
            await learn.finish(f'[{command}]只适用于在私聊中对话哦，公开性对话学习请使用[学习对话]，群内保密对话学习命令为[群内学习]')
    else:
        state["public"] = 1
    state["force_priv"] = False  # 强制不公开，输入q或a中有at信息且没有用私有学习命令时改为true并在最后将public强制设置为1
    arg = str(event.get_message())
    if arg:
        if ' 回答' not in arg:
            state['question'] = arg
        else:  # 快速学习，但插入记录仍放到对话最后处理
            question, answer = arg.split(' 回答', maxsplit=1)
            state["question"] = await msg2str(Message(question))

            answer = await msg2str(Message(answer), localize_=True, bot=bot)
            if not answer:
                await learn.finish(reply_header('这条词语好像记不住耶，要不联系主人试试？'))
            else:
                state["answer"] = answer.lstrip()  # 删除行左的空格，因为不确定用户是否会输入多个空格做回答分隔符，如果有需求可能要改逻辑


@learn.args_parser
async def parse_qa(bot: Bot, event: MessageEvent, state: T_State):
    # 退出指令
    if str(event.message) in CANCEL_EXPRESSION:
        await learn.finish('已退出当前对话') 
    # if f'[CQ:at,qq={event.self_id}]' in event.raw_message:
    #     await learn.finish('我为什么要at我自己？不要这样啦，会有bug的::>_<::')
    for seg in event.message:
        if seg.type == "at":
            # 不可以at自己
            if seg.data["qq"] == event.self_id:
                await learn.finish('我为什么要at我自己？不要这样啦，会有bug的::>_<::')
                logger.debug(f'type{type(seg.data["qq"])}')  # 检测一下type
            # 强制非公开
            if state["public"]:
                state["force_priv"] == True


@learn.got("question", '请输入问句，发送[取消]退出本次学习')
async def get_q(bot: Bot, event: MessageEvent, state: T_State):
    if "question" not in state:
        state["question"] = await msg2str(Message(event.raw_message))
    logger.debug(f'Current question is [{state["question"]}]')


@learn.got("answer", '请输入回答，发送[取消]退出本次学习')
async def get_a(bot: Bot, event: MessageEvent, state: T_State):
    question = state["question"]
    answer = state["answer"] if "answer" in state else await msg2str(Message(event.raw_message), localize_=True, bot=bot)
    if answer:
        logger.debug(f'Current answer is [{answer}]')
        source = event.group_id if event.message_type == "group" else 0
        public = 0 if state["force_priv"] else state["public"]
        result = insert(question, answer, 70, event.user_id, source, public)
        if result:
            await learn.finish(f'记录已被用户{result[0]}在{result[1]}时创建')
        else:
            exp = cgauss(5, 1, 1)
            fund = cgauss(10, 1, 1)
            user = UserLevel(event.user_id)
            await user.expup(exp, bot, event)
            user.turnover(fund)
            msg = f'对话已记录， 赠送您{exp}exp 和 {fund}金币作为谢礼~'
            if state["force_priv"]:
                msg += "\n(消息中含at信息，将强制设置公开性为群内限定)"
            msg += "当前对话相对出现率默认设置为70，如需设置出现率可直接输入0-100范围内数字，否则可忽视本条说明"
            await learn.finish(msg)
    else:
        await learn.finish(reply_header('这条词语好像记不住耶，要不联系主人试试？'))


# TODO: 设置出现率