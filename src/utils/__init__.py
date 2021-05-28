from collections import defaultdict
import time
from random import gauss
from datetime import date
from pathlib import Path
from typing import Union, Optional, Literal
from base64 import b64encode
import hmac

import httpx
from imghdr import what
from nonebot_adapter_gocq.event import MessageEvent
from nonebot_adapter_gocq.message import MessageSegment

from src.common.easy_setting import RESPATH
from src.common.dbpool import QbotDB
from src.common.log import logger


def reply_header(event: MessageEvent, text: Optional[Union[str, MessageSegment]]=None) -> MessageSegment:
    
    """快速构建一个带有回复消息头的字段

    由于私聊没太大必要回复特定消息并且当前版本有私聊中的回复消息BUG
    私聊中会返回一个空的文字段

    Args:
        event (MessageEvent): 当前消息
        text (Optional[Union[str, MessageSegment]], optional): 回复内容，文字会自动构建消息段，其他内容需要自定义消息段类型再传入

    Returns:
        MessageSegment: 连接后的消息段
    """
    logger.debug(event)
    msg = MessageSegment.reply(event.message_id) if event.message_type == 'group' else MessageSegment.text('')
    if text is not None:
        if isinstance(text, str):
            text = MessageSegment.text(text)
        msg += text
    return msg


# 用来计算某些功能给的经验和资金
def cgauss(mu: float, sigma: float, min_: Optional[int]=None, max_: Optional[int]=None) -> int:
    """一个带有钳制功能的高斯分布，并把输出变为int

    Args:
        mu ([type]): μ，高斯分布的中心
        sigma ([type]): σ，衰减
        min_ ([type], optional): 钳制最小值. Defaults to None.
        max_ ([type], optional): 钳制最大值. Defaults to None.

    Returns:
        [type]: [description]
    """
    num = round(gauss(mu, sigma))
    if min_ != None:
        num = num if num > min_ else min_
    if max_ != None:
        num = num if num < max_ else max_
    return num


async def save_img(url: str, filepath: Union[str, Path]):
    '''
    存储网络图片并将filepath文件名自动更正成正确的后缀
    '''
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=600)
    if resp.status_code != httpx.codes.OK:
        logger.error(f'Filed to request url: {url}')
        # print(f'Filed to request url: {url}')
        return
    if not isinstance(filepath, Path):
        filepath = Path(filepath)
    filepath.write_bytes(resp.content)
    real_suffix = f".{what(filepath).replace('jpeg', 'jpg')}"
    if real_suffix != filepath.suffix.lower():
        filepath.rename(filepath.with_suffix(real_suffix))
    return filepath


def imgseg(src: Union[str, Path, bytes]) -> MessageSegment:
    """以本地文件图片或二进制数据创建一个可直接发送的MessageSegment

        确认不会被和谐的图片使用此方法，否则使用antishieding模块中的Image_Hander来处理

    Args:
        path (Union[str, Path, bytes]): 文件路径或二进制文件

    Returns:
        MessageSegment: image类型
    """

    if isinstance(src, str):
        filestr = 'file:///' + src
    if isinstance(src, Path):
        filestr = 'file:///' + str(src.resolve())
    else:
        filestr = 'base64://' + b64encode(src).decode('utf-8')
    return MessageSegment.image(filestr)


def mediaseg(src: Union[str, Path], type_: Optional[Literal['image', 'record', 'video']]=None) -> MessageSegment:
    """生成图片、语音或短视频的MessageSegment

    Args:
        src (Union[str, Path]): 路径，会自动转化绝对路径
        type_ (Optional[Literal[, optional): 文件类型，如果不指定的话会依据文件后缀来判断是什么类型. Defaults to None.

    Returns:
        MessageSegment: 直接可发送的消息段
    """
    if type_ is None:
        if isinstance(src, str):
            src = Path(src)
        if src.suffix in ('.jpg', '.png', '.jpeg', '.gif'):
            return MessageSegment.image('file:///' + str(src.resolve()))
        elif src.suffix in ('.mp3', '.aac', '.amr', '.wav', '.m4a'):
            return MessageSegment.record('file:///' + str(src.resolve()))
        elif src.suffix in ('.mp4', '.flv', '.m4v'):
            return MessageSegment.video('file:///' + str(src.resolve()))
        else:
            logger.error(f'Unkwon or unsupported file format with {src}')
    else:
        return MessageSegment(type=type_, data={"file": 'file:///' + str(src.resolve())})


def link_res(filename: str, type_: str="image") -> MessageSegment:
    """快速链接本地库资源，输入文件名直接获得资源生成的MessageSegment

    Args:
        filename (str): 文件名，可有斜杠表示子文件夹
        type_ (str, optional): 资源类型 TODO：加入更多资源类型. Defaults to "image".

    Returns:
        MessageSegment: 可直接发送的消息段
    """
    if type_ == "image":
        fp = RESPATH/"images"/filename
        return imgseg(fp)  
    else:
        fp = RESPATH/filename
        return mediaseg(fp, type_)


class FreqLimiter:
    """使用此类限制每个用户的单个功能调用频率

    所有冷却列表存储在类属性next_time(dict)中
    """

    next_time = defaultdict(float)  # 剩余冷却时间，使用时应传入功能名和用户ID的组合作为key

    def __init__(self, uid: Union[str, int], func_name: str):
        """以用户ID与功能名的组合作为全局冷却字典的key

        功能名并不是分群管理规则中的sv，考虑到同一个sv中可能会有不同的功能可用，为分开计算冷却所以二者互不干扰

        Args:
            uid (Union[str, int]): 用户ID，传入后会转为str
            func_name (str): 功能名称
        """

        self.key = f'{str(uid)}{func_name}'

    def check(self) -> bool:
        return bool(time.time() >= self.__class__.next_time[self.key])

    def start_cd(self, cd_time: Union[int, float]=60):
        """清空冷却并重新开始计时

        Args:
            cd_time (int, optional): 冷却时间. Defaults to 60.
        """
        self.__class__.next_time[self.key] = time.time() + cd_time

    def left_time(self) -> float:
        return self.__class__.next_time[self.key] - time.time()


class DailyNumberLimiter:
    """使用此类限制每个用户单个功能的调用量
    """

    # 查询所有信息列表
    with QbotDB() as conn:
        # 查询数据库中所有存在的功能的名称存入列表中
        _count_tuple =  conn.queryall("SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = 'qbotdb' AND TABLE_NAME = 'calltimes' AND column_name like '%_count';")
        func_name_ls = list(map(lambda x: x[0].split('_')[0], _count_tuple))
        logger.info(f'当前数据库内功能限制列表：{str(func_name_ls)}')
        del _count_tuple

    def __init__(self, uid: int, func_name: str, max_num: int):
        """

        Args:
            uid (int): 用户ID
            func_name (str): 服务名
            max_num (int): 最大调用次数
        """
        self.conn = QbotDB()  # 注意没有使用上下文管理，要手动commit()

        # 如果没有func_name列增加三个相关列
        if func_name not in self.__class__.func_name_ls:
            logger.debug(f'A new func {func_name} will be add in table calltimes')
            self.__class__.func_name_ls.append(func_name)
            self.conn.update(f"ALTER TABLE calltimes  ADD {func_name}_day DATE, ADD {func_name}_count INT DEFAULT 0, ADD {func_name}_total INT DEFAULT 0;")
            self.conn.update(f"UPDATE calltimes SET {func_name}_day = CURDATE();")
            logger.info(f'Add func_name: {func_name} to table calltimes')
            self.conn.commit()

        result = self.conn.queryone(
            f'select {func_name}_day, {func_name}_count, {func_name}_total from calltimes where qq_number=%s;',
            (uid,)
            )  # 暂时没发现列可以通过传参方式替换的方法，只能动态拼装

        if result:
            self.last_call, self.count, self.total = result
            # 可能之前是调用其他功能时自动创建的记录所以当前功能的最后调用时间是null
            if self.last_call is None:
                self.conn.update(f"UPDATE calltimes SET {func_name}_day = CURDATE() WHERE qq_number=%s;", (uid,))
                self.conn.commit()
                self.last_call = date.today()
        else:
            # 如果没有用户记录在相关列上增加用户记录并设置为初始值
            self.conn.insert(
                f"INSERT INTO calltimes (qq_number, {func_name}_day, {func_name}_count, {func_name}_total) "
                "VALUES(%s, CURDATE(), 0, 0)",
                (uid,)
                )
            self.conn.commit()
            self.last_call, self.count, self.total = date.today(), 0, 0

        self.uid = uid
        self.func_name = func_name
        self.max_num = max_num

    def check(self, close_conn: bool=True) -> bool:
        """检查是否已超过今日最大调用量

        Args:
            close_conn (bool, optional): 是否在检查之后直接关闭连接. Defaults to True.

        Returns:
            bool: 次数小于最大调用量时为True
        """
        if self.last_call < date.today():
            self.count = 0
            self.conn.update(f'UPDATE calltimes SET {self.func_name}_count=0, {self.func_name}_day=CURDATE() WHERE qq_number=%s', (self.uid,))

        if not self.conn.q:
            self.conn.commit()
        if close_conn:
            self.conn.close()
        return self.count < self.max_num

    def increase(self, num: int=1):
        """增加调用量记录

        Args:
            num (int, optional): 增加的次数. Defaults to 1.
        """
        self.count += num
        self.total += num
        self.conn.update(f"UPDATE calltimes SET {self.func_name}_count={self.func_name}_count+1, {self.func_name}_total={self.func_name}_total+1 WHERE qq_number=%s", (self.uid,))
        self.conn.commit()
        self.conn.close()


class PagingBar:
    """
    '''一个可以翻页的分页, 支持1~10页'''
    上一页◂➀۰➁۰➌۰➃۰➄▸下一页
    Attributes:
        pgamt (int): 总页数
        crtpg (int): 当前页码
    """

    __hollowsymbols = '➀➁➂➃➄➅➆➇➈➉'
    __solidsymbols = '➊➋➌➍➎➏➐➑➒➓'

    def __init__(self, pgamt: int=3):
        """
        生成初始页码为1的分页栏

        Args:
            pgamt (int, optional): 页面数量，最大支持10页. Defaults to 3.
        """
        assert pgamt <= 10, '分页栏最大支持10页'
        self.pgamt = pgamt
        self.crtpg = 1
        serial = '۰'.join(self.__hollowsymbols[:self.pgamt])
        self.__template = self.bar = '上一页◂' + serial + '▸下一页' 
        self.turnpage(1)

    def __str__(self) -> str:
        return self.bar

    def turnpage(self, pgnumber: int) -> str:
        """
        翻到指定页面

        Args:
            pgnumber (int): 指定的页码

        Returns:
            str: 当前分页栏字符串
        """
        self.crtpg = pgnumber
        self.bar = self.__template.replace(self.__hollowsymbols[self.crtpg-1], self.__solidsymbols[self.crtpg-1])
        if self.crtpg == 1:
            self.bar = self.bar.replace('上一页', '‖')
        if self.crtpg == self.pgamt:
            self.bar = self.bar.replace('下一页', '‖')
        return self.bar

    def pgup(self) -> str:
        """上一页"""
        if self.crtpg != 1:
            self.crtpg -= 1
            self.turnpage(self.crtpg)
        return self.bar

    def pgdn(self) -> str:
        """下一页"""
        if self.crtpg != self.pgamt:
            self.crtpg += 1
            self.turnpage(self.crtpg)
        return self.bar


def get_hash_code(salt: str, msg: str):
    """获得MD5哈希值"""
    return hmac.new(key=salt.encode('utf-8'), msg=str(msg).encode('utf-8'), digestmod='MD5').hexdigest()


if __name__ == "__main__":
    pg = PagingBar(5)
    print(pg.pgdn())
    print(pg.pgup())
    print(pg.turnpage(4))