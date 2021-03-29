from typing import Optional
from random import gauss
from datetime import datetime, date
from nonebot import on_command, MatcherGroup
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from src.utils import reply_header
from src.common.levelsystem import UserLevel, exp_step
from src.common.dbpool import QbotDB


# 用来计算签到功能给的经验和资金
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



# 一个进度条用来显示经验值进度
def progress_bar(value: int, max: int) -> str:
    """进度条样式 ┃██████░░░░┃

    Args:
        value (int): 当前值
        max (int): 最大值

    Raises:
        ValueError: value can't larger than max

    Returns:
        str: 进度条样式
    """
    if value > max:
        raise ValueError("value can't larger than max")

    if max == 0:
        return '┃██████████┃'

    pct = value / max

    # 在很小或者很大的两个特殊区间会加入半个方块的字符，但无法在中间添加不然造成字符不连续
    if pct >= 0.025 and pct < 0.05:
        fill = '▐'
        empty = '░' * 9
    elif pct > 0.95 and pct <= 0.975:
        fill = '█' * 9 + '▌'
        empty = ''
    else:
        bk_amt = round(pct * 10)
        fill = '█' * round(bk_amt)
        empty = '░' * (10 - bk_amt)
    
    return '┃%s┃'%(fill + empty)


level_sys = MatcherGroup(type="message")


sign = level_sys.on_command("签到")

@sign.handle()
async def sign_(bot: Bot, event: MessageEvent):
    uid = event.user_id
    user = UserLevel(uid)

    # 是否可以签到
    today = date.today()
    last_sign_day = user.last_sign.date()

    if today > last_sign_day:
        with QbotDB() as botdb:
            botdb.update('update userinfo set `last_sign`=NOW(), total_sign=total_sign+1 where qq_number=%s;', (uid,))
        
        gndexp = cgauss(8, 2, 0)
        gndfund = cgauss(25, 3, 0)

        await user.expup(gndexp, bot, event)
        user.turnover(gndfund)
        await sign.send(reply_header(event, f'感谢签到，经验值+{gndexp}，资金+{gndfund}!'))
    
    else:
        await sign.finish(reply_header(event, '今天你已经签到过了哦~'))


query_level = level_sys.on_command('查询等级', aliases={'等级查询'})

@query_level.handle()
async def querylevel(bot: Bot, event: MessageEvent):
    uid = event.user_id
    user = UserLevel(uid)
    if event.message_type == 'group':
        name = event.sender.card or event.sender.nickname
    else:
        name = event.sender.nickname
    msg = ' {name}\n 等级：Lv.{level}\n{pg_bar}\n EXP:{exp}/{max}\n 金币:{fund} \n 最后一次签到：\n {last_sign}'.format(
        name = name,
        level = user.level,
        pg_bar = progress_bar(user.exp, exp_step(user.level)),
        exp = user.exp,
        max = exp_step(user.level),
        fund = user.fund,
        last_sign = user.last_sign if user.last_sign > datetime(2020, 11, 27) else '还未签到过'
        )
    await query_level.finish(msg)

# TODO: 连续签到天数