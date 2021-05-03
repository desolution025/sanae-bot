from pathlib import Path
import re
from asyncio import gather
import ujson as json
from math import ceil
from random import choice

import httpx
from PIL import UnidentifiedImageError
from cn2an import cn2an
from nonebot import on_regex, on_keyword
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, PrivateMessageEvent
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.message import MessageSegment
from nonebot.adapters.cqhttp.exception import NetworkError, CQHTTPAdapterException

from src.common import sl_settings
from src.common.rules import sv_sw, comman_rule
from src.common.log import logger
from src.utils import imgseg, reply_header, FreqLimiter, DailyNumberLimiter
from src.utils.antiShielding import Image_Handler
from src.common.easy_setting import MEITUPATH, SETUPATH, BOTNAME
from src.common.levelsystem import cd_step, UserLevel, FuncLimiter
from .lolicon import get_setu, get_1200
from .others import get_sjbz, get_asmdh, get_nmb, get_pw


plugin_name = '色图'
plugin_usage = """别TM搜什么孙笑川色图，诸葛亮色图了，淦
———————
设置sl只有是否最大5级才对这个有用，以下等级可以忽略
""".strip()


setu = on_regex(
    r'^ *再?[来來发發给給]?(?:(?P<num>[\d一二两三四五六七八九十]*)[张張个個幅点點份])?(?P<r18_call>[非(?:不是)]?R18)?(?P<kwd>.{0,10}?[^的])?的?(?P<r18_call2>[非(?:不是)]?R18)?的?[色瑟涩][图圖](?:(?P<num2>[\d一二两三四五六七八九十]*)[张張个個幅点點份])? *$',
    flags=re.I,
    rule=sv_sw(plugin_name, plugin_usage) & comman_rule(MessageEvent),
    priority=2
    )


@setu.handle()
async def send_lolicon(bot: Bot, event: MessageEvent, state: T_State):

    if event.message_type == 'group':
        gid = event.group_id
        if str(gid) not in sl_settings:
            await setu.finish('''先设置本群sl再使用此功能吧
[设置sl 最小sl-最大sl]
例如：设置sl 0-4
────────────
sl说明：
大概可以解释成本群能接收的工口程度，sl越高的图被人看见越会触发社死事件
※ r18权限已改为sl， 当最大sl为5时即为开启r18权限，sl0-4级别仅适用于美图，色图会自动忽略
最低sl0：不含任何ero要素，纯陶冶情操，也有一部分风景图
最高sl5: 就是R18了
中间的等级依次过渡''')

        max_sl = sl_settings[str(gid)]['max_sl']
        min_sl = sl_settings[str(gid)]['min_sl']
        restricted = True if max_sl < 5 else False  # r18是否在本群受限
    else:
        restricted = False

    # 限制条件优先度：r18，5张最大数，等级限制数量，频率，资金，由于要检测参数只好先把个别参数解析混入条款中了
    uid = event.user_id

    # r18限制条款，顺便解析了r18
    r18_call = state["_matched_dict"]['r18_call'] or state["_matched_dict"]['r18_call2']
    if r18_call and restricted:
        await setu.finish(reply_header(event, f'当前群内最大sl为{max_sl}，已禁止R18内容'))

    # 5张最大数量限制条款，顺便解析了num
    if state["_matched_dict"]['num']:
        num = cn2an(state["_matched_dict"]['num'].replace('两', '二'), 'smart')
    elif state["_matched_dict"]['num2']:
        num = cn2an(state["_matched_dict"]['num2'].replace('两', '二'), 'smart')
    else:
        num = 1

    if num > 5:
        await setu.finish(reply_header(event, '一次最多只能要5张'))
    elif num == 0:
        await setu.finish(reply_header(event, '你好奇怪的要求'))
    elif num < 0:
        await setu.finish(reply_header(event, f'好的，你现在欠大家{-num}张涩图，快发吧'))  # TODO: 想想办法把负数给提取出来

    # 等级限制数量条款，注册了用户信息
    userinfo = UserLevel(uid)
    if userinfo.level < num:
        if userinfo.level > 0:
            await setu.finish(f'您当前等级为{userinfo.level}，最多一次要{userinfo.level}张')
        elif num > 1:
            await setu.finish(reply_header(event, '啊这..0级用户一次只能叫一张哦，使用[签到]或者学习对话可以提升等级~'))

    # 频率限制条款，注册了频率限制器
    flmt = FreqLimiter(uid, 'setu')
    if not flmt.check():
        refuse = f'你冲得太快了，请{ceil(flmt.left_time())}秒后再冲'
        if userinfo.level == 0:
            refuse += '，提升等级可以加快装填哦~'
        await setu.finish(reply_header(event, refuse))  # 不用round主要是防止出现'还有0秒'的不科学情况

    # 资金限制条款，注册了每日次数限制器
    cost = num * 3 + 2
    dlmt = DailyNumberLimiter(uid, '色图', 3)
    in_free = True if event.message_type == 'private' and event.sub_type == 'friend'\
            else dlmt.check(close_conn=False)  # 来自好友的对话不消耗金币

    if userinfo.fund < cost and not in_free:
        if userinfo.fund > 0:
            refuse = f'你还剩{userinfo.fund}块钱啦，要饭也不至于这么穷吧！'
        elif userinfo.level == 0 and userinfo.fund == 0:
            refuse = '每天有三次免费次数哦，使用[签到]领取资金来获得更多使用次数吧~'
        else:
            refuse = '你已经穷得裤子都穿不起了，到底是做了什么呀？！'
        dlmt.conn.close()  # 确认直接结束不会增加调用次数了，直接返还链接
        await setu.finish(reply_header(event, refuse))

    kwd = state["_matched_dict"]['kwd'] or ''

    if r18_call:
        r18 = 1 if r18_call in ('r18', 'R18') else 0      
    else:
        if event.message_type == 'group':
            if max_sl < 5:
                r18 = 0
            elif min_sl == 5:
                r18 = 1
            elif min_sl < 5:
                r18 = 2
        else:
            r18 = 2

    # 链接API，5次错误退出并反馈错误
    logger.debug('Start getting lolicon API')
    failed_time = 0
    while failed_time < 5:
        try:
            result = await get_setu(kwd, r18, num, True)
            break
        except BaseException as e:
            failed_time += 1
            logger.exception(f"connect api faild {failed_time} time(s)\n{e}")
    else:
        logger.error(f'多次链接API失败，当前参数: kwd: [{kwd}], num: {num}, r18: {r18}')
        dlmt.conn.close()
        await setu.finish('链接API失败, 若多次失败请反馈给维护组', at_sender=True)
    logger.debug('Receive lolicon API data!')

    # 处理数据
    msg = MessageSegment.reply(id_=event.message_id) if event.message_type == 'group' else MessageSegment.text('') # 由于当前私聊回复有bug所以只在群里设置信息开始为回复消息
    if result['code'] == 0:
        count = result['count']  # 返回数量，每次处理过后自减1
        untreated_ls = []  # 未处理数据列表，遇到本地库中没有的数据要加入这个列表做并发下载
        miss_count = 0  # 丢失数量
        for data in result['data']:
            pid = data['pid']
            p = data['p']
            name = f'{pid}_p{p}'
            # 按 色图备份路径->美图原文件路径 顺序查找本地图，遇到没有本地路径的等待并发下载处理
            imgbkup = [f for f in Path(SETUPATH).glob(f'{name}.[jp][pn]*g')]
            if imgbkup:
                img = imgbkup[0]
            else:
                imgorg = [f for f in (Path(MEITUPATH)/'origin_info').rglob(f'{name}.[jp][pn]*g')]
                if imgorg:
                    img = imgorg[0]
                else:
                    untreated_ls.append(data)
                    continue
            logger.debug(f'当前处理本地图片{name}')
            info = f"{data['title']}\n画师：{data['author']}\nPID：{name}\n"
            try:
                im_b64 = Image_Handler(img).save2b64()
            except UnidentifiedImageError as imgerr:
                miss_count += 1
                logger.error(f'failed to open local file: {img}')
                continue
            msg += MessageSegment.text(info) + MessageSegment.image(im_b64)
            if count > 1:
                msg += MessageSegment.text('\n=====================\n')
                count -= 1
            elif result['count'] < num:
                msg += MessageSegment.text(f'\n=====================\n没搜到{num}张，只搜到这些了')
            
        # 对未处理过的数据进行并发下载，只下载1200做临时使用
        async with httpx.AsyncClient() as client:
            task_ls = []
            for imgurl in [d['url'] for d in untreated_ls]:
                task_ls.append(client.get(get_1200(imgurl), timeout=120))
            imgs = await gather(*task_ls, return_exceptions=True)
            
            for i, data in enumerate(untreated_ls):
                if isinstance(imgs[i], BaseException):
                    miss_count += 1
                    logger.exception(data)
                    continue
                if imgs[i].status_code != httpx.codes.OK:
                    miss_count += 1
                    logger.error(f'Got unsuccessful status_code [{imgs[i].status_code}] when visit url: {imgs[i].url}')
                    continue
                pid = data['pid']
                p = data['p']
                name = f'{pid}_p{p}'
                info = f"{data['title']}\n画师：{data['author']}\nPID：{name}\n"
                logger.debug(f'当前处理网络图片{name}')
                try:
                    im_b64 = Image_Handler(imgs[i].content).save2b64()
                except BaseException as err:
                    logger.error(f"Error with handle {name}, url: [{data['url']}]\n{err}")
                    miss_count += 1
                    continue

                msg += MessageSegment.text(info) + MessageSegment.image(im_b64)
                if count > 1:
                    msg += MessageSegment.text('\n=====================\n')
                    count -= 1
                elif result['count'] < num:
                    msg += MessageSegment.text(f'\n=====================\n没搜到{num}张，只搜到这些了')
            if miss_count > 0 and num > 1:
                msg += MessageSegment.text(f'\n有{miss_count}张图丢掉了，{BOTNAME}也不知道丢到哪里去了T_T')
            elif miss_count == 1:
                msg += MessageSegment.text(f'{BOTNAME}拿来了图片但是弄丢了呜呜T_T')

        try:
            await setu.send(msg)
        except NetworkError as err:
            logger.error(f'Maybe callout error happend: {err}')
        except CQHTTPAdapterException as err:
            logger.error(f"Some Unkown error: {err}")

        cd = cd_step(userinfo.level, 150)
        flmt.start_cd(cd)  # 开始冷却

        if miss_count < result['count']:
            if not in_free:
                cost = (result['count'] - miss_count) * 3  # 返回数量可能少于调用量，并且要减去miss的数量
                userinfo.turnover(-cost)  # 如果超过每天三次的免费次数则扣除相应资金
            dlmt.increase()  # 调用量加一
        else:
            dlmt.conn.close()

        # 下载原始图片做本地备份
        async with httpx.AsyncClient() as bakeuper:
            backup_ls = []
            json_ls = []
            for info in untreated_ls:
                url = info['url']
                json_data = {
                    'pid': info['pid'],
                    'p': info['p'],
                    'uid': info['uid'],
                    'title': info['title'],
                    'author': info['author'],
                    'url': url,
                    'r18': info['r18'],
                    'tags': info['tags']
                }
                backup_ls.append(bakeuper.get(url, timeout=500))
                json_ls.append(json_data)
            origims = await gather(*backup_ls, return_exceptions=True)
            for i, im in enumerate(origims):
                if isinstance(im, BaseException):
                    logger.exception(im)
                    continue
                if im.status_code != httpx.codes.OK:
                    logger.error(f'Got unsuccessful status_code [{im.status_code}] when visit url: {im.url}')
                    continue
                imgfp = Path(SETUPATH)/(str(json_ls[i]['pid']) + '_p' + str(json_ls[i]['p']) + '.' + json_ls[i]['url'].split('.')[-1])
                jsonfp = Path(SETUPATH)/(str(json_ls[i]['pid']) + '_p' + str(json_ls[i]['p']) + '.json')
                try:
                    with imgfp.open('wb') as f:
                        f.write(im.content)
                    logger.info(f'Downloaded image {imgfp.absolute()}')
                except BaseException as e:
                    logger.exception(e)
                with jsonfp.open('w', encoding='utf-8') as j:
                    json.dump(json_ls[i], j, ensure_ascii=False, escape_forward_slashes=False, indent=4)
                    logger.info(f'Generated json {jsonfp.absolute()}')
        return

    elif result['code'] == 404:
        await setu.finish(msg + MessageSegment.text(f'没有找到{kwd}的涩图，试试其他标签吧~'))
    elif result['code'] == 429:
        await setu.finish(msg + MessageSegment.text('今日API额度用尽了，群友们是真的很能冲呢~'))
    elif result['code'] == 401:
        await setu.finish(msg + MessageSegment.text('APIKEY貌似出了问题，请联系维护组检查'))
    else:
        await setu.finish(msg + MessageSegment.text('获取涩图失败，请稍后再试'))
    dlmt.conn.close()

#—————————————————杂项图片API—————————————————————

type_rex = re.compile(r'来张(?P<method>(?:手机)|(?:pc))?(?P<lx>.+)?壁纸')


async def call_img(bot:Bot, event: MessageEvent, state: T_State):
    """调用一些杂项图片API的规则"""

    msg = event.raw_message.lower().replace('二次元', 'acg').replace('动漫', 'acg').replace('一张', '来张').replace('电脑', 'pc').replace('妹子', '小姐姐').replace('美女', '小姐姐')
    state['pc'] = None
    if '来张小姐姐' in msg:
        state['img_type'] = 'meizi'
    elif '来张acg' in msg:
        state['img_type'] = 'acg'
    elif '来张写真' in msg:
        state['img_type'] = 'photo'
    else:
        bg_call = type_rex.search(msg)
        if bg_call:
            state['img_type'] = 'bg'
            state['pc'] = bg_call.group('method')
            state['lx'] = bg_call.group('lx')
        else:
            return False
    return True


rand_img = on_keyword({'来张', '一张'}, rule=sv_sw('杂图', '啊这..不好解释', '其它') & call_img, priority=2)
msc_img_lmt = FuncLimiter(func_name='杂图', cd_rel=150, cost=3, max_free=1, only_group=False)


@rand_img.handle()
@msc_img_lmt.inventory()
@msc_img_lmt.limit_verify(cding='下一发图片{left_time}秒后装填好~', overdraft='你只剩{left_fund}块钱了，要不考虑援交一下赚点钱？')
async def send_others(bot: Bot, event: MessageEvent, state: T_State):
    # msg = MessageSegment.reply(id_=event.message_id) if event.message_type == 'group' else MessageSegment.text('')
    if state['img_type'] == 'meizi':
        call = get_nmb(False)
    elif state['img_type'] == 'photo':
        call = get_pw(False)
    elif state['img_type'] == 'bg':
        if state['lx'] in ('acg', '小姐姐', '风景', '随机'):
            lx = state['lx'].replace('acg', 'dongman').replace('小姐姐', 'meizi').replace('风景', 'fengjing').replace('随机', 'suiji')
        elif state['lx'] is not None:
            msg = MessageSegment.text( f'没有{state["lx"]}类型的壁纸')
            await rand_img.finish(reply_header(event, msg))
        else:
            lx = 'suiji'
        if state['pc'] is not None and state['pc'] == '手机':
            state['pc'] = 'mobile'
        call = get_sjbz(state['pc'], lx)
    elif state['img_type'] == 'acg':
        call = choice((get_asmdh(), get_nmb(True), get_pw(True)))

    logger.debug(f'调用杂图API: {call.__name__}')
    try:
        result = await call
    except httpx.HTTPError as e:
        logger.exception(e)
        msg = MessageSegment.text('图片丢掉了，要不你再试试？')
        await rand_img.finish(reply_header(event, msg))

    if isinstance(result, str):
        img = MessageSegment.image(result)
    elif isinstance(result, int):
        logger.error(f'{call.__name__} 失效，状态码: {result}')
        await rand_img.finish(reply_header(event, '这个API可能挂掉了，如果一直不好使就只好停用这个功能了'))
    else:
        img = imgseg(result)
    
    await rand_img.send(reply_header(event, img))
    return 'completed'