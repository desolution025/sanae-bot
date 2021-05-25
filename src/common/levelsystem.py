from datetime import datetime
from typing import Optional
from functools import wraps
from inspect import signature

from nonebot.matcher import Matcher
from nonebot.typing import T_Handler, T_State
from nonebot_adapter_gocq.message import MessageSegment
from nonebot_adapter_gocq.exception import ActionFailed

from src.common import Bot, MessageEvent
from src.utils import reply_header, FreqLimiter, DailyNumberLimiter
from .dbpool import QbotDB
from .log import logger


def exp_step(level: int) -> int:
    """每个等级升级需要的经验值"""

    return 10 * level ** 2



def cd_step(level: int, k: int=180, alpha: float=1.5) -> int:
    """冷却步幅

    每个等级对应的冷却值的秒数, k为0级时需要的cd秒数, alpha为衰减系数，越高衰减越强烈
    冷却公式 k / (level + 1) ^ alpha, 升级收益成衰减趋势

    Args:
        level (int): 用户等钱等级
        k (int, optional): 1级时的冷却时间. Defaults to 180.
        alpha (float, optional): 衰减指数. Defaults to 1.5.

    Returns:
        int: 当前等级的冷却时间
    """    

    return round(k / (level + 1) ** alpha)


class UserLevel:
    """独立等级系统，与bot通用权限无关

    Attributes:
    uid (int): 用户ID
    level (int): 用户等级
    exp (int): 用户经验值
    fund (int): 用户资金
    last_sign (datetime.datetime): 上次签到时间
    total_sign (int): 总签到次数
    """

    def __init__(self, uid: int, level: int=0, exp: int=0, fund: int=0) -> None:
        """不存在记录时会自动创建数据

        Args:
            uid (int): 用户ID
            level (int, optional): 用户等级. Defaults to 0.
            exp (int, optional): 用户经验值. Defaults to 0.
            fund (int, optional): 用户资金. Defaults to 0.
        """
        self.uid = uid
        botdb = QbotDB()
        info = botdb.queryone(
                            'select `level`, `exp`, fund, last_sign, total_sign from userinfo where qq_number=%s',
                            (uid,)
                            )
        if info:
            self.level = info[0]
            self.exp = info[1]
            self.fund = info[2]
            self.last_sign = info[3] # 上次签到时间
            self.total_sign = info[4]
        else:
            botdb.insert(
                        "INSERT INTO userinfo (qq_number, `level`, `exp`, fund, last_sign, total_sign) "
                        "VALUES(%s, 0, 0, 0, '2020-10-05 12:22:00', 0)",
                        (uid,)
                        )
            botdb.commit()
            self.level = level
            self.exp = exp
            self.fund = fund
            self.last_sign = datetime.strptime('2020-10-05 12:22:00','%Y-%m-%d %H:%M:%S')
            self.total_sign = 0
        botdb.close()

    async def levelup(self, bot: Bot, event: Optional[MessageEvent], botdb: QbotDB, *, gid: Optional[int]=None):
        """经验值足够时提升等级并发送升级提醒

        提升等级时会把上一个等级的经验值减去

        Args:
            bot (Bot): 发送消息的bot
            event (Optional[MessageEvent]): 消息事件
            botdb (QbotDB): 数据库连接对象，由上一层函数传入
            gid (Optional[int]): 没有event传入时应指定此参数来指定发送的地点. Defaults to None.
        """

        self.exp -= exp_step(self.level)
        self.level += 1
        gndfund = self.level * 10 + 10
        self.fund += gndfund
        await self.ch_lv_notice(bot, event, botdb, up=True, gid=gid, gndfund=gndfund)

        botdb.update('update userinfo set level=%s, exp=%s, fund=%s where qq_number=%s', (self.level, self.exp, self.fund, self.uid,))
        if self.exp >= exp_step(self.level):
            await self.levelup(bot, event, botdb, gid=gid)
        else:
            return

    async def leveldown(self, bot: Bot, event: Optional[MessageEvent], botdb: QbotDB, *, gid: Optional[int]=None):
        """经验值下降时发送降级提醒

        Args:
            bot (Bot): 发送消息的bot
            event (Optional[MessageEvent]): 消息事件
            botdb (QbotDB): 数据库连接对象，由上一层函数传入
            gid (Optional[int], optional): 没有event传入时应指定此参数来指定发送的地点. Defaults to None.
        """
        self.exp += exp_step(self.level - 1)
        self.level -= 1
        await self.ch_lv_notice(bot, event, botdb, up=False, gid=gid)

        botdb.update('update userinfo set level=%s, exp=%s where qq_number=%s', (self.level, self.exp, self.uid,))

        if self.exp < 0 and self.level > 0:
            await self.leveldown(bot, event, botdb, gid=gid)
        else:
            return

    async def ch_lv_notice(self, bot: Bot, event: Optional[MessageEvent], botdb: QbotDB, up: bool=True, *, gid: Optional[int]=None, gndfund: Optional[int]=None):
        """等级变动提醒

        Args:
            bot (Bot): 发送消息的bot对象
            event (Optional[MessageEvent]): 主动触发的事件对象，有可能是由于其它事件而被动触发，则此处为None
            botdb (QbotDB): 数据库连接对象，应有上一层调用函数中传入
            up (bool, optional): 是否是升级，决定发送的对话. Defaults to True.
            gid (Optional[int], optional): event为None时则必须传入int型参数，作为发送事件的目标群. Defaults to None.
            gndfund (Optional[int], optional): up为True时应传入此参数以发送升级奖励的具体数字提醒，不传入也可二次计算. Defaults to None.
        """

        msg = '{name}升级到lv{level}了！获得{gndfund}金币~' if up else '{name}的等级降到{level}了，好遗憾的说(憋笑~~)'

        if event is not None:
            if event.message_type == 'group':
                name = event.sender.card or event.sender.nickname or event.get_user_id()
            else:
                name = event.sender.nickname or event.get_user_id()
            gndfund = gndfund if gndfund is not None else self.level * 10 + 10
            await bot.send(event, message=msg.format(name=name, level=self.level, gndfund=gndfund), at_sender=True)
        else:
            assert isinstance(gid, int), '未传入event参数时必须获得int型的gid参数'
            try:
                member = await bot.get_group_member_info(group_id=gid, user_id=self.uid)
            except ActionFailed as e:
                logger.warning(f'可能是已经退群的群员: group: {gid} qq: {self.uid}, error: {e}')
                await bot.send_group_msg(group_id=gid, message=f'本应该在群内的成员({self.uid})貌似获取不到了，是不是退群了呢？没有的话请联系维护组查看一下出问题的原因哦~')
                return
            name = member['card'] or member['nickname'] or str(self.uid)

            await bot.send_group_msg(group_id=gid, message=MessageSegment.text(msg.format(name=name, level=self.level)) + MessageSegment.at(qq=self.uid))

    async def expup(self, value: int, bot: Bot, event: Optional[MessageEvent]=None, *, gid: Optional[int]=None):
        """提升经验值
        
        需要传入bot、event参数给升级事件发送消息用，调用升级时传出conn对象更新数据用

        Args:
            value (int): 提升的经验
            bot (Bot): 传给升级事件的Bot对象
            event (Optional[MessageEvent]): 传给升级事件的Event对象，不传入时则必须指定gid来确定发送消息的群
        """
        self.exp += value
        with QbotDB() as botdb:
            if self.exp >= exp_step(self.level): # 检测经验值是否超过本级上限，是则升级
                await self.levelup(bot, event, botdb, gid=gid)
            elif self.exp < 0 and self.level > 0:  # 只有等级大于0的时候才能降级，否则直接往下扣 
                await self.leveldown(bot, event, botdb, gid=gid)
            else:
                botdb.update('update userinfo set `exp`=%s where qq_number=%s;', (self.exp, self.uid,))

    def turnover(self, value: int, *, check_overdraft: bool=True):
        """花费资金，持有资金小于要花费的金额时提示透支

        Args:
            value (int): 资金变动值，向外花费资金应该为负数
            check_overdraft (bool): 是否检查透支，如果不检查则无论如何都减去金币，资金可能变为负.Default is True.

        Returns:
            tuple[int, bool]: 执行后的资金以及是否透支
        """
        if check_overdraft and value < 0:
            if self.fund + value > 0:
                self.fund += value
                overdraft = False

                with QbotDB() as botdb:
                    botdb.update('update userinfo set fund=%s where qq_number=%s', (self.fund, self.uid))
            else:
                overdraft = True
        else:
            self.fund += value
            with QbotDB() as botdb:
                    botdb.update('update userinfo set fund=%s where qq_number=%s', (self.fund, self.uid))
            overdraft = self.fund < 0

        return self.fund, overdraft


def is_user(uid: int) -> bool:
    """查询是否是使用过bot的用户"""

    with QbotDB() as qb:
        result = qb.queryone("SELECT 1 FROM userinfo WHERE qq_number=%s AND (`exp`>0 OR `level`>0) LIMIT 1;", (uid,))
    return bool(result)

def filter_users(*uids):
    """过滤出使用过bot的用户"""

    with QbotDB() as qb:
        users = []
        if len(uids) > 1:
            result = qb.queryall(f"SELECT qq_number FROM userinfo WHERE qq_number in {tuple(uids)}")
            if result:
                users = [i[0] for i in result]
        else:
            if is_user(uids[0]):
                users = [uids[0]]
    return users

class FuncLimiter:
    """集成各种条件的功能限制器

    使用limit_verify方法作为装饰器时按冷却->今日调用量->资金依次判断是否有可以调用功能
    使用inventory方法作为装饰器时在函数return 'completed'后自动计算冷却、调用量、消耗金币
    作用于同一handler时需按照
    @[Matcher.method()]
    @inventory()
    @limit_verify()
    的顺序进行装饰
    """

    def __init__(self,
                func_name: str,
                cd_rel: int=180,
                max_free: int=0,
                cost: int=0,
                *,
                cd_c: bool=False,
                max_limit: bool=False,
                only_group: bool=True
                ) -> None:
        """生成限制器实例

        注意不想共同计算的功能要设置不一样的func_name

        Args:
            func_name (str): 功能名，相同功能名的限制器实例会共用同一个冷却、最大调用量
            cd_rel (int, optional): 1级冷却，传给cd_step的k，非必须，也可设置恒定冷却. Defaults to 180.
            max_free (int, optional): 每日最大调用次数，为0则不限制. Defaults to 0.
            cost (int, optional): 功能花费金额. Defaults to 0.
            cd_c (bool, optional): 冷却是否为恒定值，否则根据等级计算. Defaults to False.
            max_limit (bool, optional): 最大调用量限制，默认会在达到最大免费次数后自动消耗金币获得调用权限，为True时则无法使用金币获得额外调用量. Defaults to False.
            only_group (bool, optional): True则不会在私聊中进行任何限制. Defaults to True.
        """
        self.func_name, self.cd_rel, self.max_free, self.cost, self.cd_c, self.max_limit, self.only_group\
            = func_name, cd_rel, max_free, cost, cd_c, max_limit, only_group

    def limit_verify(self,
                    cding: str='功能冷却还有{left_time}秒，请稍等一会儿',
                    out_max: str='今日本功能调用次数已用尽',
                    overdraft :str='你的资金剩余为{left_fund}金币',
                    ):
        """
        一个根据用户等级与资金判断可否调用功能的函数，用作装饰器

        被装饰函数除了bot还必须拥有event参数
        执行自动计算冷却、消耗金币等操作请使用inventory装饰器
        拒绝语句中剩余资金和剩余冷却可以用format分别传入{left_fund}和{left_time}替换

        Args:
            cding (str, optional): 冷却中提醒语句. Defaults to '功能冷却还有{left_time}秒，请稍等一会儿'.
            out_max (str, optional): 超过每日调用次数上限提醒语句. Defaults to '今日本功能调用次数已用尽'.
            overdraft (str, optional): 超额提醒语句. Defaults to '你的资金剩余为{left_fund}金币'.
            only_group (bool, optional): True则不会在私聊中进行任何限制. Defaults to True.
        """
        def deco(func: T_Handler):
            # @wraps(func)  TODO: inventory一起装饰的时候会出错，想办法把wraps加上
            async def wrapper(bot: Bot, event: MessageEvent, state: T_State, matcher: Matcher):
                # 只在群内检测，检测顺序为频率>每日限制>资金
                logger.debug('开始检测')
                if not (self.only_group is True and event.message_type == 'private'):
                    uid = event.user_id

                    flmt = FreqLimiter(uid, self.func_name)
                    if not flmt.check():
                        left_time = flmt.left_time()
                        msg = cding.format(left_time=round(left_time))
                        await matcher.finish(reply_header(event, msg))
                    logger.debug('频率检测通过')

                    nlmt = DailyNumberLimiter(uid, self.func_name, self.max_free)
                    in_free = nlmt.check()
                    if self.max_limit:
                        if self.max_free == 0:
                            await matcher.finish(reply_header(event, '此功能关闭中...'))
                        if not in_free:
                            await matcher.finish(reply_header(event, out_max))
                    logger.debug('每日调用限制检测通过')

                    if self.cost and not in_free:
                        userinfo = UserLevel(uid)
                        if userinfo.fund < self.cost:
                            refuse_msg = overdraft.format(left_fund = userinfo.fund)
                            if userinfo.level == 0:
                                refuse_msg += '，先[签到]领取资金吧'
                            await matcher.finish(reply_header(event, refuse_msg))
                    logger.debug('资金检测通过')

                return await self.call_source(func, bot, event, state, matcher)

            return wrapper
        return deco

    def inventory(self, branch='completed'):
        """完成命令之后自动扣除金币、计算冷却等操作

        考虑到调用了函数但未完成完整功能调用的情况，功能调用成功的分支里要手动return 'completed'

        Args:
            branch (str, optional): 完整执行了命令的分支返回的标识字符串(其实不用字符串也行). Defaults to 'completed'.
        """

        def deco(func: T_Handler):
            @wraps(func)
            async def wrapper(bot:Bot, event: MessageEvent, state: T_State, matcher: Matcher):
                result = await self.call_source(func, bot, event, state, matcher)

                logger.debug(f'{func.__name__}返回结果: {result}')
                # 执行完命令获得返回值，如果是'completed'代表完整执行了命令，此时扣除资金并开始冷却
                if not (self.only_group is True and event.message_type == 'private') and result == branch:
                    logger.debug(f'{func.__name__}完整执行，进行结算')
                    uid = event.user_id
                    userinfo = UserLevel(uid)

                    nlmt = DailyNumberLimiter(uid, self.func_name, self.max_free)
                    if self.max_free:
                        if self.cost and not nlmt.check(close_conn=False):
                            userinfo.turnover(-self.cost)
                    elif self.cost:
                        userinfo.turnover(-self.cost)
                    nlmt.increase()

                    cd = cd_step(userinfo.level, self.cd_rel) if not self.cd_c else self.cd_rel
                    FreqLimiter(uid, self.func_name).start_cd(cd)
                
            return wrapper
        return deco

    async def call_source(self, func: T_Handler, bot: Bot, event: MessageEvent, state: T_State, matcher: Matcher):
        """解析handler参数并赋予真实参数调用"""

        params = signature(func)
        _bot = params.parameters.get('bot')
        _event = params.parameters.get('event')
        _state = params.parameters.get('state')
        _matcher = params.parameters.get('matcher')
        args = []
        for i, param in enumerate([_bot, _event, _state, _matcher]):
            if param:
                args.append([bot, event, state, matcher][i])
        return await func(*args)


if __name__ == "__main__":
    for i in range(10):
        print(cd_step(i, k=180, alpha=1.5))