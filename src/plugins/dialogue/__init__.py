from pathlib import Path
from typing import Optional, Union
from collections import namedtuple, defaultdict
import re
import asyncio
from urllib.request import urlretrieve
from random import choice, randint

from emoji import emojize, demojize
from imghdr import what
from nonebot import MatcherGroup
from nonebot.message import handle_event

from src.common import Bot, MessageEvent, GroupMessageEvent, PrivateMessageEvent, Message, MessageSegment, T_State, CANCEL_EXPRESSION, SUPERUSERS, BOTNAME
from src.common.rules import sv_sw, full_match
from src.common.log import logger
from src.common.levelsystem import UserLevel
from src.utils import reply_header, cgauss, PagingBar
from .corpus import query, query_exists, plus_one, insertone, insertmany, update_prob, del_record


plugin_name = '问答对话'
plugin_usage = """
﹟ 使用学习功能可增加经验值与资产，支持图片、emoji
﹟ 学习之后的内容会按照出现概率进行回复，短时间内不会回复重复的内容
﹟ 设置的概率为相对概率，实际的概率会根据相同对话的条目数与对话地点进行调整
———————
发送以下指令查看相应的使用方式(带上两边的Q和A)
Q学习方法A
Q查询方法A
Q修改方法A
Q批量学习A
""".strip()


#—————————————————功能说明——————————————————


guide = MatcherGroup(type='message', priority=2)


learn_method = guide.on_message(rule=full_match('Q学习方法A'))
query_method = guide.on_message(rule=full_match('Q查询方法A'))
modify_method = guide.on_message(rule=full_match('Q修改方法A'))
batch_learn_method = guide.on_message(rule=full_match('Q批量学习A'))


@learn_method.handle()
async def guide_learn(bot: Bot):
    await learn_method.finish(""">>>学习方法：
﹟ [学习 问句 回答 答句] 可快速设置对话，记得用空格做分隔，
﹟ 不方便连续发送的内容(如内容中包含图片)可单独发送[学习]然后按照说明输入
﹟ 可分别在私聊和群中使用[私聊学习]和[群内学习]进行仅能在学习地点出现的对话
   (也就是群内学习的内容不会在其它群内散播，私聊学习的内容仅仅只能创建人在私聊中触发)
﹟ 答句里使用{name}可在回复时自动替换掉触发者的昵称(带上中括号)
   例：答句：我{name}就是饿死也不会女装！
      在被昵称为 强哥 的用户触发对话时会自动变为：我强哥就是饿死也不会女装！

※※ 看不懂就只使用一个[学习]就行了""")


@query_method.handle()
async def guide_query(bot: Bot):
    await query_method.finish(""">>>查询方法：
﹟ [查询对话 问题内容]根据查询信息返回可能会触发的对话
﹟ 由于图太多了会突破发图数量限制造成封号，暂时设置了翻页查看，还在改进中
﹟ [历史学习 随意信息]模糊查询自己设置过的对话(还未开放使用)(还没写__)""")


@modify_method.handle()
async def guide_modify(bot: Bot):
    await modify_method.finish(""">>>修改&删除方法
﹟ 刚刚学习过对话之后可直接输入0-100范围内的数字作为相对出现率，默认70%
﹟ [修改出现率 -对话ID -出现率数字]可重新设置某个对话的出现率，例：修改出现率 -2234 -80
﹟ [删除对话 对话ID]并不会删除对话，而是会将对话的出现率设置为0，则此对话任何时候不会出现，但仍可之后重新调整出现率

※※v0.0.14之前学习的内容普遍设置为了50，有大量内容需要修改回100%触发的可联系维护组""")


@batch_learn_method.handle()
async def guide_batch_learn(bot: Bot):
    await batch_learn_method.finish(""">>>批量学习
﹟ [批量学习] 输入内容中使用 "|" 做分隔符，则会将问句与回答做排列组合一起学习
例： <问> 群主大人|管理sama <答> 不是好人|变态|流氓|女装犯|后宫男宠三千万
    则出现“群主大人”或“管理sama”的对话时会随机触发答句中的某个赞美信息(如果通过了触发率的条件下)
﹟ 同样支持[批量私聊学习] [批量群内学习]""")


#———————————————————————————————————————


CORPUS_IMAGES_PATH = (Path(r'.\res')/'images'/'corpus_imgs').resolve()


def localize(url: str, filename: str, failed_times: int=0) -> Optional[str]:
    """本地化图片存储在语料库图片文件夹

    Args:
        url (str): 要下载的url
        filename (str): 下载后存储的文件名称
        failed_times (int, optional): 初始失败次数. Defaults to 0.

    Returns:
        Optional[str]: 成功下载会返回下载后的文件储存路径，否则返回None
    """

    searchfile = CORPUS_IMAGES_PATH.glob(filename.split('.')[0] + ".*")
    for f in searchfile:
        fp = f
        logger.debug(f'File [{filename}] has localized with {fp}')
        return fp.name
    fp = CORPUS_IMAGES_PATH/filename
    try:
        urlretrieve(url, fp)
        realpath = fp.with_suffix('.' + what(fp))  # 修复文件为真正的后缀
        fp.rename(realpath)
        logger.info(f'Localize image [{filename}] with path: {realpath.name}')
        return realpath.name
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
        bot (Optional[Bot]): 本地化处理时需要传入bot对象调用获得图片信息api

    Returns:
        str: 转换后的字符串
    """

    strcq = ''
    for seg in message:
        logger.debug('Handle segment: ', str(seg), 'type: ', seg.type)
        if seg.type == 'text':
            strcq += demojize(str(seg))
        elif seg.type == 'image':
            if not localize_:
                strcq += f'[CQ:image,file={seg.data["file"]}]'
            else:
                imginfo = await bot.get_image(file=seg.data["file"])
                realname = localize(imginfo["url"], seg.data["file"])
                if not realname:
                    return None
                strcq += f'[CQ:image,file=file:///{{res_path}}\\{realname}]'
        else:
            strcq += str(seg)
    return strcq


def msglize(msg: str, name: str="{name}", prestr: bool=False) -> Union[Message, str]:
    """解析数据库answer时调用，把返回消息中的{res_path}替换为真实资源路径, 把{name}换成昵称并去转义emoji

    Args:
        msg (str): 数据库中的answer
        name (str, optional): 要替换{name}字段的字符，通常为event.sender.card|nickname. Defaults to "{name}".
        prestr (bool): 是否要保持字符串，使用此选项不会把消息转为Message而是会保持为字符串返回. Defaults to False.

    Returns:
        Union[Message, str]: 解析后自动转换Message或保持str
    """
    if '[CQ:image,' in msg or "{name}" in msg:
        msg = msg.format(res_path=str(CORPUS_IMAGES_PATH), name=name)
    if prestr:
        return emojize(msg)
    else:
        return Message(emojize(msg))  # 由于nb2使用array上报数据所以要实例化为Message可直接转化旧版字符串数据


class Pagination:
    """为防止列表过长造成刷屏或超出单次发送长度限制，生成一个分页查看的问答记录列表

    最大10页，超过的数量将被裁剪掉 TODO: 把过长的页面内容放到网页上
    
    Attributes:
        rcd_ls (dict): 页码和内容组成的字典.
        crupg (int): 当前实例所在的页码.
        pagebar (PagingBar): 分页栏.
    """

    def __init__(self, *records) -> None:
        """
        传入记录列表，通常为查询数据库之后将结果分别字符串化后的列表
        """

        self.rcd_ls = defaultdict(str)
        container = 0
        cruprint = 1
        for record in records:  # 每页容器大小为9，带有图片的记录为3，其它为1，循环为分页内容分配记录，容器大小满时分配下一页
            if container >= 9:
                cruprint += 1
                container = 0
            cost = 3 if '[CQ:image,' in record else 1
            self.rcd_ls[cruprint] += record
            container += cost
        total = len(self.rcd_ls)
        logger.info(f'Generate records list with {total} page(s)')
        if total > 10:
            logger.info(f'Too many records to show, clip to 10 pages')
            while total > 10:
                self.rcd_ls.popitem()
                total -= 1
        self.crupg = 1
        self.pagebar = PagingBar(total)
    
    def __str__(self) -> str:
        return self.rcd_ls[self.crupg] + str(self.pagebar)
        
    def turnpage(self, pgnumber: int):
        self.crupg = pgnumber
        self.pagebar.turnpage(pgnumber)
        return self.__str__()

    def pgup(self):
        if self.crupg != 1:
            self.crupg -= 1
            self.pagebar.pgup()
        return self.__str__()

    def pgdn(self):
        if self.crupg != len(self.rcd_ls):
            self.crupg += 1
            self.pagebar.pgdn()
        return self.__str__()


qanda = MatcherGroup(type='message', rule=sv_sw('问答对话', plugin_usage))


#—————————————————回复——————————————————


async def reply_checker(bot: Bot, event: MessageEvent, state: T_State) -> bool:
    """问答对话触发规则"""
    q = await msg2str(Message(event.raw_message))  # 仅仅使用message会去掉呼唤bot昵称的原文本，造成问句中有bot昵称时逻辑混乱
    logger.debug(f'Search question <{q}> in corpus...')
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


#———————————————单次学习————————————————


def filter_selflearn(bot: Bot, event: MessageEvent, state: T_State):
    """过滤非bot管理员的自学"""
    if event.message.extract_plain_text().startswith('自学') and event.user_id not in SUPERUSERS:
        return False
    return True


preprob = {}  # 出现率设置预备列表，在其中的用户刚使用了学习对话功能
learn = qanda.on_command('学习', aliases={'学习对话', '群内学习', '私聊学习', '偷偷学习', '自学'}, rule=sv_sw('问答对话', plugin_usage)&filter_selflearn)
SANAE_BOTS = (1538482349, 2503554271, 1431906058, 2080247830, 2021507926, 2078304161, 1979853134, 2974922146, 1670225564)
ALLOW_SEGMENT = ('text', 'face', 'image', 'at', 'record', 'video', 'share')  # 允许学习的CQ码


@learn.handle()
async def first_receive(bot: Bot, event: MessageEvent, state: T_State):
    
    # 过滤妖精的早苗
    if event.user_id in SANAE_BOTS:
        await learn.finish('两只AI成功握手，但被主人阻止掉了(;∀;)')

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
        if command == '自学':
            state["selflearn"] = True
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
                await learn.finish(reply_header(event, '这条词语好像记不住耶，要不联系主人试试？'))
            else:
                state["answer"] = answer.lstrip()  # 删除行左的空格，因为不确定用户是否会输入多个空格做回答分隔符，如果有需求可能要改逻辑


@learn.args_parser
async def parse_qa(bot: Bot, event: MessageEvent, state: T_State):
    # 退出指令
    if str(event.message) in CANCEL_EXPRESSION:
        await learn.finish('已退出当前对话') 
    # if f'[CQ:at,qq={event.self_id}]' in event.raw_message:
    #     await learn.finish('我为什么要at我自己？不要这样啦，会有bug的::>_<::')
    for seg in Message(event.raw_message):
        if seg.type == "at":
            # 不可以at自己
            if seg.data["qq"] == str(event.self_id):
                await learn.finish('我为什么要at我自己？不要这样啦，会有bug的::>_<::')
                logger.info('User is setting at botself, cancel learning')  # 检测一下type
            # 强制非公开
            if state["public"]:
                state["force_priv"] = True
                logger.info('Got at info, force set public to 0')
        # 不能存入消息的格式
        if seg.type not in ALLOW_SEGMENT:
            if seg.type == 'reply':
                await learn.finish('请不要学习带有回复上文消息的内容，会引发定位错误')
            else:
                await learn.finish('接收的消息不在可学习范围内')


@learn.got("question", '请输入问句，发送[取消]退出本次学习')
async def get_q(bot: Bot, event: MessageEvent, state: T_State):
    if "question" not in state:
        state["question"] = await msg2str(Message(event.raw_message))
    logger.debug(f'Current question is [{state["question"]}]')


@learn.got("answer", '请输入回答，发送[取消]退出本次学习')
async def get_a(bot: Bot, event: MessageEvent, state: T_State):
    question = state["question"]
    answer = state["answer"] if "answer" in state else await msg2str(Message(event.raw_message), localize_=True, bot=bot)
    if len(question) > 255 or len(answer) > 255:
        await learn.finish(f'内容太长的对话{BOTNAME}记不住的说＞﹏＜')
    if answer:
        logger.debug(f'Current answer is [{answer}]')
        source = event.group_id if event.message_type == "group" else 0
        public = 0 if state["force_priv"] else state["public"]
        creator = event.user_id if 'selflearn' not in state else event.self_id
        logger.info(f'Insert record to corpus :\nquestion:[{question}]\nanswer:[{answer}]\npublic:{public}\ncreator:{creator}\nsource:{source}')
        result = insertone(question, answer, 70, creator, source, public)
        if isinstance(result, tuple):
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
            msg += "\n﹟ 当前对话相对出现率默认设置为70，如需设置出现率可直接输入0-100范围内数字，否则可忽视本条说明"
            preprob[event.user_id] = result
            await learn.finish(msg)
    else:
        await learn.finish(reply_header(event, '这条词语好像记不住耶，要不联系主人试试？'))


def get_prob_checker(bot: Bot, event: MessageEvent, state: T_State):
    """获得出现率触发规则"""
    if event.user_id not in preprob:
        return False

    state["sid"] = preprob[event.user_id]
    del preprob[event.user_id]  # 触发学习后续设置之后直接删除预备列表中的当前用户

    if not event.raw_message.isdigit():
        return False
    prob = int(event.raw_message)
    if prob >= 0 and prob <= 100:
        state["prob"] = prob
        return True
    else:
        return False


get_prob = qanda.on_message(rule=get_prob_checker, priority=2)  # 此对话需要比触发对话的优先级更高防止用户设置了简单的数字对话内容而不能触发此对话


@get_prob.handle()
async def set_prob(bot: Bot, event: MessageEvent, state: T_State):
    update_prob(state["sid"], state["prob"])
    await get_prob.finish(reply_header(event, f'好的，已将刚才学习对话的相对出现率调整为{state["prob"]}%'))


#———————————————批量学习————————————————


def filter_selflearn(bot: Bot, event: MessageEvent, state: T_State):
    """过滤非bot管理员的批量自学"""
    if event.message.extract_plain_text().startswith('批量自学') and event.user_id not in SUPERUSERS:
        return False
    return True


batch_learn = qanda.on_command('批量学习', aliases={'群内批量学习', '批量群内学习', '私聊批量学习', '批量私聊学习', '批量自学'})


@batch_learn.handle()
async def start_learn(bot: Bot, event: MessageEvent, state: T_State):
    command = state["_prefix"]["raw_command"]
    if command in ('群内批量学习', '批量群内学习'):
        if isinstance(event, GroupMessageEvent):
            state["public"] = 0
        else:
            await learn.finish(f'[{command}]只适用于在群中对话哦，公开性批量对话学习请使用[批量学习]，私聊内保密批量对话学习命令为[批量私聊学习]')
    elif command in ('私聊批量学习', '批量私聊学习'):
        if isinstance(event, PrivateMessageEvent):
            state["public"] = 0
        else:
            await learn.finish(f'[{command}]只适用于在私聊中对话哦，公开性批量对话学习请使用[批量学习]，群内保密对话学习命令为[批量群内学习]')
    else:
        if command == '自学':
            state["selflearn"] = True
        state["public"] = 1
    state["force_priv"] = False  # 强制不公开，输入q或a中有at信息且没有用私有学习命令时改为true并在最后将public强制设置为1


@batch_learn.args_parser
async def parse_batch_qa(bot: Bot, event: MessageEvent, state: T_State):
    # 退出指令
    if str(event.message) in CANCEL_EXPRESSION:
        await learn.finish('已退出当前对话') 
    for seg in Message(event.raw_message):
        if seg.type == "at":
            # 不可以at自己
            if seg.data["qq"] == event.self_id:
                await learn.finish('我为什么要at我自己？不要这样啦，会有bug的::>_<::')
                logger.debug(f'type{type(seg.data["qq"])}')  # 检测一下type
            # 强制非公开
            if state["public"]:
                state["force_priv"] == True
        # 不能存入消息的格式
        if seg.type not in ALLOW_SEGMENT:
            if seg.type == 'reply':
                await learn.finish('请不要学习带有回复上文消息的内容，会引发定位错误')
            else:
                await learn.finish('接收的消息不在可学习范围内')


@batch_learn.got('question', prompt='请输入问句，多个问句可使用“|”分隔，发送退出本次学习')
async def batch_get_q(bot: Bot, event: MessageEvent, state: T_State):
    state["question"] = await msg2str(Message(event.raw_message))
    logger.debug(f'Current question is [{state["question"]}]')
    qs = event.raw_message.split("|")
    qs_i = [f'{i + 1}.{q}' for i, q in enumerate(qs)]
    msg = Message('当前要记录的问句为：\n' + '\n'.join(qs_i) + '\n请确认以上问句无误，输入回答内容，使用“|”分隔，否则请发送[取消]结束对话重新输入')
    await batch_learn.send(msg)


@batch_learn.got('answer')
async def batch_get_a(bot: Bot, event: MessageEvent, state: T_State):
    answer = await msg2str(Message(event.raw_message), localize_=True, bot=bot)
    if answer:
        state["answer"] = answer
    else:
        await batch_learn.finish(reply_header(event, '含有学习失败的信息，要不联系主人试试？'))
    logger.debug(f'Current answer is [{answer}]')
    ans = event.raw_message.split("|")
    as_i = [f'{i + 1}.{a}' for i, a in enumerate(ans)]
    msg = Message('当前要记录的回答为：\n' + '\n'.join(as_i) + '\n请确认以上回答无误，输入相对出现率[0-100]，否则请发送[取消]结束对话重新输入')
    await batch_learn.send(msg)
    state['wrong_times'] = 0  # 输入错误次数，用于获取出现率时计算


@batch_learn.receive()
async def batch_get_prob(bot: Bot, event: MessageEvent, state: T_State):
    if str(event.message) in CANCEL_EXPRESSION:
        await learn.finish('已退出当前对话') 
    if not event.raw_message.isdigit():
        state['wrong_times'] += 1
        if state['wrong_times'] < 3:
            await batch_learn.reject(prompt='请输入数字参数作为相对出现率，范围[0-100]，请重新输入，发送[取消]结束当前学习对话')
        else:
            await batch_learn.finish('看来你是不想好好说了，就这样吧，挂了')

    prob = int(event.raw_message)
    if prob < 0 or prob > 100:
        state['wrong_times'] += 1
        if state['wrong_times'] < 3:
            await batch_learn.reject(prompt='输入范围应该是[0-100]，请重新输入，发送[取消]结束当前学习对话')
        else:
            await batch_learn.send('不要闹了，我先帮你设置成50了，要该的话之后用[设置出现率]来改吧')
            asyncio.sleep(1)  # 停一秒防止设置成功的消息和此条消息顺序出错

    public = 0 if state["force_priv"] else state["public"]
    source = event.group_id if event.message_type == "group" else 0
    creator = event.user_id if 'selflearn' not in state else event.self_id
    result = insertmany(state["question"].split('|'), state["answer"].split('|'), prob, creator, source, public)
    if isinstance(result, int):
        exp = cgauss(5, 1, 1) + result - 1
        fund = cgauss(10, 1, 1) + result - 1
        user = UserLevel(event.user_id)
        await user.expup(exp, bot, event)
        user.turnover(fund)
        msg = f'已记录{result}条对话，赠送您{exp}exp 和 {fund}金币作为谢礼~'
        if state["force_priv"]:
            msg += "\n(消息中含at信息，将强制设置公开性为群内限定)"
    else:
        repeat_ls = [f"问句：{emojize(q)} 回答：{a} 被{creator}在{creation_time}创建" for q, a, creator, creation_time in result]
        msg = f'以下对话已存在：\n' + '\n'.join(repeat_ls) + '\n请去除重复对话后重新学习'
    await batch_learn.finish(msg)


#—————————————————查询——————————————————


query_record = qanda.on_command('查询', aliases= {'查询对话', '搜索对话'}, priority=2)


@query_record.args_parser
async def pass_input(bot: Bot, event: MessageEvent, state: T_State):
    # 阻止分段对话时自动传入state因为要使用不同的message来源
    pass


@query_record.handle()
async def recieve_query(bot: Bot, event: MessageEvent, state: T_State):
    arg = await msg2str(Message(event.message))
    if arg:
        state["question"] = arg


@query_record.got('question', prompt='请输入要查询的问句')
async def handle_query(bot: Bot, event: MessageEvent, state: T_State):
    question = state["question"] if 'question' in state else await msg2str(Message(event.raw_message))
    logger.debug(f'Query question in corpus: [{question}]')
    gid = event.group_id if event.message_type == 'group' else 0
    result = query(question, gid, q=True)

    if not result:
        await query_record.finish(Message(f'没找到关于 ') + Message(question) + (Message(' 的对话')))
    
    Record = namedtuple('Record', ['sid', 'answer', 'probability', 'creator', 'source', 'creation_time', 'public'])
    result = map(lambda x: Record(*x), result)

    # 群里不把私聊中非公开对话列出，私聊中不把非自己创建的私聊非公开对话列出，用作最终显示数据
    result = [r for r in result if not (r.public == 0 and r.source == 0 and (event.message_type == 'group' or event.message_type != 'group' and event.user_id != r.creator))]

    def sort_rule(r: Record) -> int:
        """按照本群限定>本群创建但公开>其它群创建但公开>其它群限定的顺序排列"""

        if r.source == gid:
            priority = 1 if not r.public else 2
        else:
            priority = 3 if r.public else 4
        return priority

    result.sort(key=sort_rule)

    # 可能在当前对话窗口出现的内容，把出现率是0、不在此群或私聊创建的非公开选项排除，用作计算绝对出现率
    possible = [r for r in result if not (r.probability == 0 or (not r.public and r.source != gid))]
    possible_count = len(possible)

    result_ls = [f'''ID：{sid}
回答：{msglize(answer, prestr=True)}
相对出现率：{probability}%
绝对出现率：{0 if not public and source != gid else round(probability / possible_count, 2)}%
创建者：{creator}
来自：{('群聊 ' + str(source)) if source else '私聊 '}
公开性：{'公开' if public else '群内限定'}
创建时间：
{creation_time}
────────────
''' for sid, answer, probability, creator, source, creation_time, public in result]
    # TODO: 把回复里的音频和视频分离出来变成'[音频][视频]'

    record_bar = Pagination(*result_ls)
    if len(record_bar.rcd_ls) == 1:
        msg = ''.join(result_ls)
        await query_record.finish(reply_header(event, Message(msg + '使用"[修改出现率] <对话id> <出现率>"来修改指定对话的相对出现率\n例：修改出现率 -2234 -10')))
    else:
        state["record_bar"] = record_bar
        state['left_wrong_times'] = 3
        await query_record.send(reply_header(event, Message(str(record_bar) + '\n发送[上一页][下一页]翻页查看列表，发送<序号>跳转到指定页，发送[退出]退出当前查询')))


@query_record.receive()
async def look_over(bot: Bot, event: MessageEvent, state: T_State):
    op = str(event.message.extract_plain_text())
    if not op:
        await query_record.reject()
    if op in CANCEL_EXPRESSION:
        await query_record.finish('已退出查询页面')
    if op.strip().startswith('修改出现率'):
        await handle_event(bot, event)
        # 如果不能一次输入参数的话两个对话会同时进行产生冲突，参数数量不符合时会直接结束查询对话
        if len(op.strip('-')) == 3:
            await query_record.reject()
        else:
            await query_record.finish()
    bar :Pagination = state["record_bar"]
    addend = '\n发送[上一页][下一页]翻页查看列表，发送<页面序号>跳转到指定页\n使用 [修改出现率] <对话id> <出现率> 来修改指定对话的相对出现率\n发送[退出]退出当前查询'
    if op == "上一页":
        if bar.crupg == 1:
            msg = '当前已经是首页了哦~'
            state['left_wrong_times'] -= 1
        else:
            msg = bar.pgup() + addend
    elif op == '下一页':
        if bar.crupg == len(bar.rcd_ls):
            msg = '已经是最后页了~'
            state['left_wrong_times'] -= 1
        else:
            msg = bar.pgdn() + addend
    elif op.isdigit():
        pgnum = int(op)
        if pgnum > 0 and pgnum <= len(bar.rcd_ls):
            msg = bar.turnpage(pgnum) + addend
        else:
            msg = '超出当前已有的页面范围了~'
            state['left_wrong_times'] -= 1
    elif state['left_wrong_times'] > 0:
        msg = f"未期望的输入，{state['left_wrong_times']}次输入错误将退出查询对话，发送[退出]退出当前查询"
        state['left_wrong_times'] -= 1
    else:
        await query_record.finish('未期望的输入，已退出当前查询对话')

    await query_record.reject(Message(msg))


#—————————————————修改——————————————————


modify = qanda.on_command('修改出现率', priority=2)


@modify.handle()
async def parse_1st(bot: Bot, event: MessageEvent, state: T_State):
    args = [s.strip() for s in event.message.extract_plain_text().split('-')[1:]]
    for arg in args:
        if not arg.isdigit():
            await modify.finish(reply_header(event, '不符合格式的输入，仅支持数字id与出现率'))
    if len(args) > 2:
        await modify.finish(reply_header(event, '不符合参数数量的输入'))
    elif len(args) == 2:
        state["sid"], state["prob"] = [int(i) for i in args]
    elif len(args) == 1:
        state["sid"] = int(args[0])


@modify.args_parser
async def parse_num(bot: Bot, event: MessageEvent, state: T_State):
    # 退出指令
    if str(event.message) in CANCEL_EXPRESSION:
        await learn.finish('已退出当前对话')
    # 赋值整数参数
    if not event.raw_message.isdigit():
        await modify.finish(reply_header(event, '只接受数字参数'))
    state[state["_current_key"]] = int(event.raw_message)


@modify.got("sid", prompt='请输入要修改的对话ID，发送[退出]取消修改')
async def get_sid(bot: Bot, event: MessageEvent, state: T_State):
    sid = state["sid"]
    if result := query_exists(sid, q=True):
        creator, source, public = result
        gid = event.group_id if event.message_type == 'group' else 0
        if not public and source != gid and creator != event.user_id and event.user_id not in SUPERUSERS:  # 查询地点无法触发的非公开对话且不为查询者创建，不能修改
            await modify.finish(reply_header(event, '此对话为他人创建非公开对话，您没有权限更改此对话出现率'))
    else:
        await modify.finish(reply_header(event, f'ID {sid} 的对话不存在，请检查查询内容'))


@modify.got("prob", prompt='请输入相对出现率，范围0-100，发送[退出]取消修改')
async def get_probability(bot: Bot, event: MessageEvent, state: T_State):
    prob = state["prob"]
    if prob < 0 or prob > 100:
        await modify.finish(reply_header(event, '出现率仅接收0-100范围内的数字参数'))
    update_prob(state["sid"], prob)
    await modify.finish(f'已将id为{state["sid"]}的对话相对出现率修改为{prob}%')


delete_record = qanda.on_command('删除对话', priority=2)  # 普通用户并不会删除对话，而是调用修改分辨率对话然后将对话出现率设置为0


@delete_record.handle()
async def fake_del_recieve(bot: Bot, event: MessageEvent, state: T_State):
    arg = event.message.extract_plain_text().strip()
    if arg:
        state["sid"] = arg  # 不需要转换int，参数统一放入message发送修改出现率命令


@delete_record.got("sid", '请输入要删除的ID，输入[取消]结束本次对话')
async def fake_del_handle(bot: Bot, event: MessageEvent, state: T_State):
    # 退出指令
    if str(event.message) in CANCEL_EXPRESSION:
        await delete_record.finish('已退出当前对话')
    sid = state["sid"] if "sid" in state else event.message.extract_plain_text().strip()
    if event.user_id in SUPERUSERS:  # 真实的删除
        try:
            sid = int(sid)
        except ValueError:
            await delete_record.finish(reply_header(event, '非数字参数'))
        exsit = query_exists(sid)
        if not exsit:
            await delete_record.finish(reply_header(event, '不存在的对话'))
        del_record(sid)
        await delete_record.finish(reply_header(event, f'已删除对话{sid}'))
    else:  # 虚假的删除
        event.message = Message(f'修改出现率 -{sid} -0')
        await handle_event(bot, event)


# TODO: 查询自己设置过的，举报，修改随机算法，先预计算所有会出现的对话再choice