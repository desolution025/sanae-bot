from pathlib import Path
from io import BytesIO
import base64
import re
from asyncio import gather
import ujson as json
import httpx
from PIL import Image
from imghdr import what
from nonebot import on_regex
from nonebot.rule import Rule
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.message import MessageSegment
from cn2an import cn2an
from src.common.rules import sv_sw, comman_rule
from src.common.log import logger
from src.utils import imgseg
from src.utils.antiShielding import handleimage, changPixel, gen_b64
from src.common.easy_setting import MEITUPATH
from .lolicon import get_setu, get_1200


plugin_name = '色图'


BACKUPFP = './res/images/setu'
# setu = on_keyword(('色图', '涩图'), rule=comman_rule(MessageEvent))
# seturex = re.compile(r'再?[来來发發给給]?(?:(?P<num>[\d一二两三四五六七八九十]*)[张張个個幅点點份])?(?P<r18_call>[rR]18)?(?P<kwd>.{0,11}[^的])?的?[色瑟涩][图圖](?:(?P<num2>[\d一二两三四五六七八九十]*)[张張个個幅点點份])?')


setu = on_regex(
    r'^再?[来來发發给給]?(?:(?P<num>[\d一二两三四五六七八九十]*)[张張个個幅点點份])?(?P<r18_call>[非(?:不是)]?R18)?(?P<kwd>.{0,10}?[^的])?的?(?P<r18_call2>[非(?:不是)]?R18)?的?[色瑟涩][图圖](?:(?P<num2>[\d一二两三四五六七八九十]*)[张張个個幅点點份])?$',
    flags=re.I,
    rule=comman_rule(MessageEvent)
    )


@setu.handle()
async def parse_args(bot: Bot, event: MessageEvent, state: T_State):
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
            
    try:
        result = await get_setu(kwd, r18, num, True)
    except Exception as e:
        logger.error(e)
        await setu.finish('链接API失败, 若多次失败请反馈给维护组', at_sender=True)
    
    msg = MessageSegment.reply(id_=event.message_id) if event.message_type == 'group' else MessageSegment.text('')
    if result['code'] == 0:
        count = result['count']  # 返回数量，每次处理过后自减1
        untreated_ls = []  # 未处理数据列表，遇到本地库中没有的数据要加入这个列表做并发下载
        for data in result['data']:
            pid = data['pid']
            p = data['p']
            name = f'{pid}_p{p}'
            # 查找本地路径，查找顺序依次为 美图反和谐路径->色图备份路径->美图原文件路径，遇到没有本地路径的等待并发下载处理
            imgad = [f for f in (Path(MEITUPATH)/'antishielding').glob(f'{name} (antishieded).*')]
            if imgad:
                img = imgseg(imgad[0])
            else:
                imgbkup = [f for f in Path(BACKUPFP).glob(f'{name}.[jp][pn]*g')]
                if imgbkup:
                    img = gen_b64(imgbkup[0])
                else:
                    imgorg = [f for f in (Path(MEITUPATH)/'origin_info').rglob(f'{name}.[jp][pn]*g')]
                    if imgorg:
                        img = imgseg(handleimage(imgorg[0]))
                    else:
                        untreated_ls.append(data)
                        continue

            info = f"{data['title']}\n画师：{data['author']}\nPID：{pid}\n"
            msg += MessageSegment.text(info) + MessageSegment.image(img)
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
            imgs = await gather(*task_ls)
            for i, data in enumerate(untreated_ls):
                info = f"{data['title']}\n画师：{data['author']}\nPID：{data['pid']}\n"
                imgbuffer = BytesIO(imgs[i].content)
                with Image.open(imgbuffer) as bf:
                    adimg = changPixel(bf)
                adimg.save(imgbuffer, format='jpeg', quality=90)
                im_b64 = "base64://" + base64.b64encode(imgbuffer.getvalue()).decode('utf-8')

                msg += MessageSegment.text(info) + MessageSegment.image(im_b64)
                if count > 1:
                    msg += MessageSegment.text('\n=====================\n')
                    count -= 1
                elif result['count'] < num:
                    msg += MessageSegment.text(f'\n=====================\n没搜到{num}张，只搜到这些了')

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
            origims = await gather(*backup_ls)
            for i, im in enumerate(origims):
                imgfp = Path(BACKUPFP)/(str(json_ls[i]['pid']) + '_p' + str(json_ls[i]['p']) + '.' + json_ls[i]['url'].split('.')[-1])
                jsonfp = Path(BACKUPFP)/(str(json_ls[i]['pid']) + '_p' + str(json_ls[i]['p']) + '.json')
                try:
                    with imgfp.open('wb') as f:
                        f.write(im.content)
                    logger.info(f'Downloaded image {imgfp.absolute()}')
                except Exception as e:
                    logger.error(e)
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

    # TODO: 可能要把并发写成函数并且加入异常捕获