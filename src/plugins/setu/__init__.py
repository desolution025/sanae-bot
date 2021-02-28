from pathlib import Path
import re
from asyncio import gather
import ujson as json
from random import choice
import httpx
from nonebot import on_regex, on_keyword
from nonebot.rule import Rule
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.message import MessageSegment
from cn2an import cn2an
from src.common.rules import sv_sw, comman_rule
from src.common.log import logger
from src.utils import imgseg
from src.utils.antiShielding import Image_Handler
from src.common.easy_setting import MEITUPATH, SETUPATH, BOTNAME
from .lolicon import get_setu, get_1200
from .others import get_sjbz, get_asmdh, get_nmb, get_pw


plugin_name = '色图'


# SETUPATH = './res/images/setu'
# setu = on_keyword(('色图', '涩图'), rule=comman_rule(MessageEvent))
# seturex = re.compile(r'再?[来來发發给給]?(?:(?P<num>[\d一二两三四五六七八九十]*)[张張个個幅点點份])?(?P<r18_call>[rR]18)?(?P<kwd>.{0,11}[^的])?的?[色瑟涩][图圖](?:(?P<num2>[\d一二两三四五六七八九十]*)[张張个個幅点點份])?')


setu = on_regex(
    r'^ *再?[来來发發给給]?(?:(?P<num>[\d一二两三四五六七八九十]*)[张張个個幅点點份])?(?P<r18_call>[非(?:不是)]?R18)?(?P<kwd>.{0,10}?[^的])?的?(?P<r18_call2>[非(?:不是)]?R18)?的?[色瑟涩][图圖](?:(?P<num2>[\d一二两三四五六七八九十]*)[张張个個幅点點份])? *$',
    flags=re.I,
    rule=comman_rule(MessageEvent)
    )


@setu.handle()
async def send_lolicon(bot: Bot, event: MessageEvent, state: T_State):
    kwd = state["_matched_dict"]['kwd'] or ''

    if state["_matched_dict"]['num']:
        num = cn2an(state["_matched_dict"]['num'].replace('两', '二'), 'smart')
    elif state["_matched_dict"]['num2']:
        num = cn2an(state["_matched_dict"]['num2'].replace('两', '二'), 'smart')
    else:
        num = 1

    if num > 5:
        await setu.finish('一次最多只能要5张', at_sender=True)
    elif num == 0:
        await setu.finish('你好奇怪的要求', at_sender=True)
    elif num < 0:
        await setu.finish(f'好的，你现在欠大家{-num}张涩图，快发吧', at_sender=True)

    r18_call = state["_matched_dict"]['r18_call'] or state["_matched_dict"]['r18_call2']
    if r18_call:
        r18 = 1 if r18_call in ('r18', 'R18') else 0      
    else:
        r18 = 2
    
    # await setu.finish(f'kwd: [{kwd}], r18: {r18}, num: {num}\n_matcged: {state["_matched"]}, _matched_groups: {state["_matched_groups"]}')

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
        await setu.finish('链接API失败, 若多次失败请反馈给维护组', at_sender=True)
    
    msg = MessageSegment.reply(id_=event.message_id) if event.message_type == 'group' else MessageSegment.text('') # 由于当前私聊回复有bug所以只在群里设置信息开始为回复消息
    if result['code'] == 0:
        count = result['count']  # 返回数量，每次处理过后自减1
        untreated_ls = []  # 未处理数据列表，遇到本地库中没有的数据要加入这个列表做并发下载
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
            msg += MessageSegment.text(info) + MessageSegment.image(Image_Handler(img).save2b64())
            if count > 1:
                msg += MessageSegment.text('\n=====================\n')
                count -= 1
            elif result['count'] < num:
                msg += MessageSegment.text(f'\n=====================\n没搜到{num}张，只搜到这些了')
            
        # 对未处理过的数据进行并发下载，只下载1200做临时使用
        async with httpx.AsyncClient() as client:
            task_ls = []
            for imgurl in [d['url'] for d in untreated_ls]:
                task_ls.append(client.get(get_1200(imgurl), timeout=90))
            imgs = await gather(*task_ls, return_exceptions=True)
            miss_acount = 0
            for i, data in enumerate(untreated_ls):
                if isinstance(data, BaseException):
                    miss_acount += 1
                    logger.exception(data)
                    continue
                pid = data['pid']
                p = data['p']
                name = f'{pid}_p{p}'
                info = f"{data['title']}\n画师：{data['author']}\nPID：{name}\n"
                logger.debug(f'当前处理网络图片{name}')
                try:
                    im_b64 = Image_Handler(imgs[i].content).save2b64()
                except BaseException as err:
                    logger.exception(f"Error with handle {name}, url: [{data['url']}]\n{err}")
                    miss_acount += 1
                    continue

                msg += MessageSegment.text(info) + MessageSegment.image(im_b64)
                if count > 1:
                    msg += MessageSegment.text('\n=====================\n')
                    count -= 1
                elif result['count'] < num:
                    msg += MessageSegment.text(f'\n=====================\n没搜到{num}张，只搜到这些了')
            if miss_acount > 0 and num > 1:
                msg += MessageSegment.text(f'\n有{miss_acount}张图丢掉了，{BOTNAME}也不知道丢到哪里去了T_T')
            elif miss_acount == 1:
                msg += MessageSegment.text(f'{BOTNAME}拿来了图片但是弄丢了呜呜T_T')

        await setu.send(msg)

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

    
    elif result['code'] == 404:
        await setu.finish(msg + MessageSegment.text(f'没有找到{kwd}的涩图，试试其他标签吧~'))
    elif result['code'] == 429:
        await setu.finish(msg + MessageSegment.text('今日API额度用尽了，群友们是真的很能冲呢~'))
    elif result['code'] == 401:
        await setu.finish(msg + MessageSegment.text('APIKEY貌似出了问题，请联系维护组检查'))
    else:
        await setu.finish(msg + MessageSegment.text('获取涩图失败，请稍后再试'))


#——————————————————————————————————————

type_rex = re.compile(r'来张(?P<method>(?:手机)|(?:pc))?(?P<lx>.+)?壁纸')

async def call_img(bot:Bot, event: MessageEvent, state: T_State):
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


rand_img = on_keyword({'来张', '一张'}, rule=call_img, priority=2)

@rand_img.handle()
async def send_others(bot: Bot, event: MessageEvent, state: T_State):
    msg = MessageSegment.reply(id_=event.message_id) if event.message_type == 'group' else MessageSegment.text('')
    if state['img_type'] == 'meizi':
        call = get_nmb(False)
    elif state['img_type'] == 'photo':
        call = get_pw(False)
    elif state['img_type'] == 'bg':
        if state['lx'] in ('acg', '小姐姐', '风景', '随机'):
            lx = state['lx'].replace('acg', 'dongman').replace('小姐姐', 'meizi').replace('风景', 'fengjing').replace('随机', 'suiji')
        elif state['lx'] is not None:
            msg += MessageSegment.text( f'没有{state["lx"]}类型的壁纸')
            await rand_img.finish(msg)
        else:
            lx = 'suiji'
        if state['pc'] is not None and state['pc'] == '手机':
            state['pc'] = 'mobile'
        call = get_sjbz(state['pc'], lx)
    elif state['img_type'] == 'acg':
        call = choice((get_asmdh(), get_nmb(True), get_pw(True)))

    try:
        result = await call
    except httpx.HTTPError as e:
        logger.exception(e)
        msg += MessageSegment.text('图片丢掉了，要不你再试试？')
        await rand_img.finish(msg)

    if isinstance(result, str):
        img = MessageSegment.image(result)
    else:
        img = imgseg(result)
    
    await rand_img.finish(msg + img)