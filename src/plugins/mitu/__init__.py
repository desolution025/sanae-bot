import re
from math import ceil

from nonebot import on_regex, MatcherGroup
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.message import MessageSegment
from cn2an import cn2an

from src.common.rules import sv_sw, comman_rule
from src.utils import reply_header, FreqLimiter, DailyNumberLimiter
from src.utils.antiShielding import Image_Handler
from src.common import sl_settings, save_sl
from src.common.easy_setting import BOTNAME, SUPERUSERS
from src.common.levelsystem import UserLevel, cd_step
from src.common.log import logger
from .mitu_lib import get_mitu


plugin_name = '美图'
plugin_usage = """还没完善，可以先忽略本功能
关于设置sl：
sl说明：
大概可以解释成本群能接收的工口程度，sl越高的图被人看见越会触发社死事件
!!!!!没有那种不属于人类的XP!!!!!
最低sl0：不含任何ero要素，纯陶冶情操，也有一部分风景图
最高sl5: 就是R18了
中间的等级依次过渡
────────────
[设置sl 最小sl-最大sl]
例如：设置sl 0-4
[锁定sl] 管理锁定之后群员不可设置sl，且锁定权限依据操作者权限
例如：群主锁定，管理员不可解锁；管理员锁定，群主可解锁但群员不可解锁
[解锁sl] 解锁之后群员可随意设置sl
[查询sl] 查看本群当前设置
[本群评级] 未开放(要写，没写，画线去掉)
────────────
""".strip()

#——————————————————设置sl——————————————————


lock_map = {
    'member': 0,
    'admin': 1,
    'owner': 2
    }  # 把群权限转成int方便比较


lock_inv_map = {
    0: '群员',
    1: '管理员',
    2: '群主'
    }  # 还要映射回来，好蠢，淦


sl = MatcherGroup(rule=comman_rule(GroupMessageEvent))


set_sl = sl.on_command('设置sl', aliases={'设置SL', '设置Sl'})


@set_sl.handle()
async def setsl_(bot: Bot, event: GroupMessageEvent, state: T_State):
    gid = str(event.group_id)
    locked = sl_settings[gid]['locked'] if gid in sl_settings else lock_map[event.sender.role]
    if locked > lock_map[event.sender.role] and event.user_id not in SUPERUSERS:
        await set_sl.finish(reply_header(event, f'sl被{lock_inv_map[locked]}锁定，低于此权限不可设置sl，或先以高级权限[解锁sl]重置锁定权限'))
    args = event.get_plaintext().strip()
    if not args:
        await set_sl.finish('请输入本群sl等级范围，如：设置sl 0-4\n(最小0， 最大5)\n※注意是范围！几到几，不是单纯一个数字！')
    parse =args.split('-')
    if  len(parse) == 2 and parse[0].isdigit() and parse[1].isdigit():
        min_sl = int(parse[0])
        max_sl = int(parse[1])
        if min_sl < 0 or min_sl > 5 or max_sl < 0 or max_sl > 5:
            await set_sl.finish(reply_header(event, '设置的数字必须在0~5区间'))
        if min_sl > max_sl:
            min_sl, max_sl = max_sl, min_sl
    else:
        await set_sl.finish(reply_header(event, '不符合格式的设置，比如：设置sl 0-4'))

    gid = str(event.group_id)
    sl_settings[gid]['min_sl'] = min_sl
    sl_settings[gid]['max_sl'] = max_sl
    sl_settings[gid]['locked'] = lock_map[event.sender.role]

    if save_sl():
        await set_sl.finish(f'已设置本群sl为[{min_sl}-{max_sl}]')  # TODO：设置sl评级
    else:
        await set_sl.finish('设置sl功能故障，请联系维护组紧急修复！')


lock_sl = sl.on_command('锁定sl', aliases={'锁定SL', '锁定Sl'})


@lock_sl.handle()
async def lock_sl_(bot: Bot, event: GroupMessageEvent):
    gid = str(event.group_id)
    if gid not in sl_settings:
        await lock_sl.finish('本群未设置sl')
    if event.sender.role not in ('owner', 'admin'):
        await lock_sl.finish('仅管理权限可锁定sl')
    min_sl = sl_settings[gid]['min_sl']
    max_sl = sl_settings[gid]['max_sl']
    locked = sl_settings[gid]['locked']
    if locked:
        await lock_sl.finish(f'已经锁了，现在sl区间是[{min_sl}-{max_sl}]')
    else:
        sl_settings[gid]['locked'] = lock_map[event.sender.role]
        if save_sl():
            await set_sl.finish(f'已锁定本群sl为[{min_sl}-{max_sl}]，管理员使用[解锁sl]功能可解除锁定')
        else:
            await set_sl.finish('sl功能故障，请联系维护组紧急修复！')


unlock_sl = sl.on_command('解锁sl', aliases={'解锁SL', '解锁Sl'})


@unlock_sl.handle()
async def unlock_sl_(bot: Bot, event: GroupMessageEvent):
    gid = str(event.group_id)
    if gid not in sl_settings:
        await lock_sl.finish('本群未设置sl')
    locked = sl_settings[gid]['locked']
    if not locked:
        await lock_sl.finish('本群sl未锁定')
    if locked > lock_map[event.sender.role]:
        await lock_sl.finish(reply_header(event, f'sl被{lock_inv_map[locked]}锁定，低于此权限不可解锁sl'))
    sl_settings[gid]['locked'] = 0
    if save_sl():
        await set_sl.finish('已解锁sl，当前sl区间可由群员设置')
    else:
        await set_sl.finish('sl功能故障，请联系维护组紧急修复！')


# 查询当前群sl区间
query_sl = sl.on_command('查询sl', aliases={'查询SL', '查询Sl', '本群sl', '本群SL', '本群Sl'})


@query_sl.handle()
async def report_sl(bot: Bot, event: GroupMessageEvent):
    gid = str(event.group_id)
    if gid not in sl_settings:
        await query_sl.finish('本群未设置sl')
    min_sl = sl_settings[gid]['min_sl']
    max_sl = sl_settings[gid]['max_sl']
    locked = sl_settings[gid]['locked']
    msg = f'本群sl区间为:[{min_sl}-{max_sl}]\n'
    if not locked:
        msg += '未锁定'
    else:
        msg += f'被{lock_inv_map[locked]}锁定'
    await query_sl.finish(reply_header(event, msg))

#——————————————————————————————————————————————————


mitu = on_regex(
    r'^ *再?[来來发發给給]?(?:(?P<num>[\d一二两三四五六七八九十]*)[张張个個幅点點份])?(?P<r18_call>[非(?:不是)]?R18)?(?P<kwd>.{0,10}?[^的])?的?(?P<r18_call2>[非(?:不是)]?R18)?的?美[图圖](?:(?P<num2>[\d一二两三四五六七八九十]*)[张張个個幅点點份])? *$',
    flags=re.I,
    rule=sv_sw(plugin_name, usage=plugin_usage) & comman_rule(GroupMessageEvent),
    priority=2
    )


kwdrex = re.compile(r'[,，]')  # 分离逗号做交集搜索


@mitu.handle()
async def send_mitu(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 设置sl
    gid = event.group_id
    if str(gid) not in sl_settings:
        await mitu.finish('''先设置本群sl再使用此功能吧
[设置sl 最小sl-最大sl]
例如：设置sl 0-4
────────────
sl说明：
大概可以解释成本群能接收的工口程度，sl越高的图被人看见越会触发社死事件
最低sl0：不含任何ero要素，纯陶冶情操，也有一部分风景图
最高sl5: 就是R18了
中间的等级依次过渡''')

    min_sl = sl_settings[str(gid)]['min_sl']
    max_sl = sl_settings[str(gid)]['max_sl']

    # 限制条件优先度：r18，5张最大数，等级限制数量，频率，资金，由于要检测参数只好先把个别参数解析混入条款中了
    uid = event.user_id

    # r18限制条款，顺便解析了r18
    r18_call = state["_matched_dict"]['r18_call'] or state["_matched_dict"]['r18_call2']
    if r18_call and max_sl < 5:
        await mitu.finish(reply_header(event, f'当前群内最大sl为{max_sl}，不是5的话{BOTNAME}发不出R18图片哦~'))

    # 5张最大数量限制条款，顺便解析了num
    if state["_matched_dict"]['num']:
        num = cn2an(state["_matched_dict"]['num'].replace('两', '二'), 'smart')
    elif state["_matched_dict"]['num2']:
        num = cn2an(state["_matched_dict"]['num2'].replace('两', '二'), 'smart')
    else:
        num = 1

    if num > 5:
        await mitu.finish(reply_header(event, '一次最多只能要5张'))
    elif num == 0:
        await mitu.finish(reply_header(event, '你好奇怪的要求'))
    elif num < 0:
        await mitu.finish(reply_header(event, f'好的，你现在欠大家{-num}张涩图，快发吧'))  # TODO: 想想办法把负数给提取出来

    # 等级限制数量条款，注册了用户信息
    userinfo = UserLevel(uid)
    if userinfo.level < num:
        if userinfo.level > 0:
            await mitu.finish(f'您当前等级为{userinfo.level}，最多一次要{userinfo.level}张')
        elif num > 1:
            await mitu.finish(reply_header(event, '啊这..0级用户一次只能叫一张哦，使用[签到]或者学习对话可以提升等级~'))



    # 频率限制条款，注册了频率限制器
    flmt = FreqLimiter(uid, 'mitu')
    if not flmt.check():
        refuse = f'再等{ceil(flmt.left_time())}秒才能继续发图'
        if userinfo.level == 0:
            refuse += '，提升等级可以缩短冷却时间哦~'
        await mitu.finish(reply_header(event, refuse))  # 不用round主要是防止出现'还有0秒'的不科学情况

    # 资金限制条款，注册了每日次数限制器
    cost = num * 3 + 2
    dlmt = DailyNumberLimiter(uid, '美图', 3)
    in_free = dlmt.check(close_conn=False)

    if userinfo.fund < cost and not in_free:
        if userinfo.fund > 0:
            refuse = f'你还剩{userinfo.fund}块钱啦，要饭也不至于这么穷吧！'
        elif userinfo.level == 0 and userinfo.fund == 0:
            refuse = '每天有三次免费次数哦，使用[签到]领取资金来获得更多使用次数吧~'
        else:
            refuse = '你已经穷得裤子都穿不起了，到底是做了什么呀？！'
        dlmt.conn.close()  # 确认直接结束不会增加调用次数了，直接返还链接
        await mitu.finish(reply_header(event, refuse))

    kwd = state["_matched_dict"]['kwd']
    if kwd:
        kwds = tuple(kwdrex.split(kwd))
    else:
        kwds = ()

    if r18_call:
        min_sl = 5

    success, result = get_mitu(event.group_id, kwds, num, min_sl, max_sl)
    if not success:
        dlmt.conn.close()
        await mitu.finish(reply_header(event, result))
        
    miss_count = 0  # 丢失的图片数量
    count = len(result)  # 返回数量，每次处理过后自减1
    msg = MessageSegment.text('')
    for data in result:
        if not data:
            miss_count += 1
            count -= 1
            continue
        info = f"{data['title']}\n作者：{data['author']}\n来源：{data['source']}\n"
        image = Image_Handler(data['file']).save2b64()
        msg += MessageSegment.text(info) + MessageSegment.image(image)
        if count > 1:
            msg += MessageSegment.text('\n=====================\n')
            count -= 1
        elif len(result) < num:
            msg += MessageSegment.text(f'\n=====================\n没搜到{num}张，只搜到这些了')
    if miss_count > 0:
        if len(result) > 1:
            msg += MessageSegment.text(f'\n有{miss_count}张图丢掉了，{BOTNAME}去联系主人修复一下~')
        else:
            msg += MessageSegment.text(f'{BOTNAME}拿来图片但是丢掉了，我问问主人他看到没T_T')
        for su in SUPERUSERS:
            await bot.send_private_msg(user_id=su, message='貌似图库出了问题，错误记录在日志里了')

    await mitu.send(reply_header(event, msg))

    cd = cd_step(userinfo.level, 150)
    flmt.start_cd(cd)  # 开始冷却

    if miss_count < len(result):
        if not in_free:
            cost = (len(result) - miss_count) * 3  # 返回数量可能少于调用量，并且要减去miss的数量
            userinfo.turnover(-cost)  # 如果超过每天三次的免费次数则扣除相应资金
        dlmt.increase()  # 调用量加一
    else:
        dlmt.conn.close()
