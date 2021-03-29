from datetime import datetime
from functools import wraps
from typing import Callable
from random import gauss
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
try:
    from .dbpool import QbotDB
    from .log import logger
except:
    pass
from src.utils import reply_header, FreqLimiter, DailyNumberLimiter


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

    async def levelup(self, bot: Bot, event: MessageEvent, botdb: QbotDB):
        """经验值足够时提升等级并发送升级提醒

        提升等级时会把上一个等级的经验值减去

        Args:
            bot (Bot): 发送消息的bot
            event (MessageEvent): 消息事件
            botdb (QbotDB): 数据库连接对象，由上一层函数传入
        """

        self.exp -= exp_step(self.level)
        self.level += 1
        gndfund = self.level * 10 + 10
        self.fund += gndfund
        if event.message_type == 'group':
            name = event.sender.card or event.sender.nickname or event.get_user_id()
        else:
            name = event.sender.nickname or event.get_user_id()
        botdb.update('update userinfo set level=%s, exp=%s, fund=%s where qq_number=%s', (self.level, self.exp, self.fund, self.uid,))

        await bot.send(event, message=f'{name}升级到lv{self.level}了！获得{gndfund}金币~', at_sender=True)
        if self.exp >= exp_step(self.level):
            await self.levelup(bot, event, botdb)
        else:
            return

    async def expup(self, value: int, bot: Bot, event: MessageEvent):
        """提升经验值
        
        需要传入bot、event参数给升级事件发送消息用，调用升级时传出conn对象更新数据用

        Args:
            value (int): 提升的经验
            bot (Bot): 传给升级事件的Bot对象
            event (MessageEvent): 传给升级事件的Event对象
        """
        self.exp += value
        with QbotDB() as botdb:
            if self.exp >= exp_step(self.level): # 检测经验值是否超过本级上限，是则升级
                await self.levelup(bot, event, botdb)
            else:
                botdb.update('update userinfo set `exp`=%s where qq_number=%s;', (self.exp, self.uid,))

    def turnover(self, value: int):
        """花费资金，持有资金小于要花费的金额时提示透支

        Args:
            value (int): 资金变动值，向外花费资金应该为负数

        Returns:
            tuple[int, bool]: 执行后的资金以及是否透支
        """
        if self.fund + value > 0:
            self.fund += value
            overdraft = False

            with QbotDB() as botdb:
                botdb.update('update userinfo set fund=%s where qq_number=%s', (self.fund, self.uid))
        else:
            overdraft = True

        return self.fund, overdraft


class FuncLimiter:
    """集成各种条件的功能限制器

    使用limit_verify方法作为装饰器时按冷却->今日调用量->资金依次判断是否有可以调用功能
    使用inventory方法作为装饰器时在函数return 'completed'后自动计算冷却、调用量、消耗金币
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
        def deco(func: Callable):
            @wraps(func)
            async def wrapper(bot: Bot, event: MessageEvent, *args, **kw):

                # 只在群内检测，检测顺序为频率>每日限制>资金
                if not (self.only_group is True and event.message_type == 'private'):
                    uid = event.user_id

                    flmt = FreqLimiter(uid, self.func_name)
                    if not flmt.check():
                        left_time = flmt.left_time()
                        msg = cding.format(left_time=round(left_time))
                        await bot.send(event, reply_header(event, msg))
                        return

                    if self.max_limit:
                        if self.max_free == 0:
                            await bot.send(event, reply_header(event, '此功能关闭中...'))
                            return
                        nlmt = DailyNumberLimiter(uid, self.func_name, self.max_free)
                        if not nlmt.check():
                            await bot.send(event, reply_header(event, out_max))
                            return
                        else:
                            self.daily_pass = True

                    if self.cost:
                        userinfo = UserLevel(uid)
                        if userinfo.fund < self.cost:
                            refuse_msg = overdraft.format(left_fund = userinfo.fund)
                            if userinfo.level == 0:
                                refuse_msg += '，先[签到]领取资金吧'
                            await bot.send(event, reply_header(refuse_msg))
                            return

                return await func(bot, event, *args, **kw)

            return wrapper
        return deco

    def inventory(self):
        """完成命令之后自动扣除金币、计算冷却等操作

        考虑到调用了函数但未完成完整功能调用的情况，功能调用成功的分支里要手动return 'completed'
        """
        def deco(func: Callable):
            @wraps(func)
            async def wrapper(bot: Bot, event: MessageEvent, *args, **kw):
                result = await func(bot, event, *args, **kw)
                # 执行完命令获得返回值，如果是'completed'代表完整执行了命令，此时扣除资金并开始冷却
                if not (self.only_group is True and event.message_type == 'private') and result == 'completed':
                    uid = event.user_id
                    userinfo = UserLevel(uid)

                    if self.max_free:
                        nlmt = DailyNumberLimiter(uid, self.func_name, self.max_free)
                        if self.cost and not nlmt.check(close_conn=False):
                            userinfo.turnover(-self.cost)
                        nlmt.increase()

                    elif self.cost:
                        userinfo.turnover(-self.cost)

                    cd = cd_step(userinfo.level, self.cd_rel) if not self.cd_c else self.cd_rel
                    FreqLimiter(uid, self.func_name).start_cd(cd)
                
            return wrapper
        return deco


if __name__ == "__main__":
    for i in range(10):
        print(cd_step(i, k=180, alpha=1.5))