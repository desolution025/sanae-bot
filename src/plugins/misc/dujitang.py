from pathlib import Path
import ujson as json
from datetime import datetime
from random import choice
from asyncio import sleep as asleep
from apscheduler.schedulers.base import BaseScheduler

from nonebot import require, MatcherGroup
from nonebot_adapter_gocq.bot import Bot
from nonebot_adapter_gocq.event import GroupMessageEvent
from nonebot_adapter_gocq.permission import GROUP
from nonebot_adapter_gocq.exception import ActionFailed
from nonebot.log import logger

from src.common import show_gb_dict
from src.common.dbpool import QbotDB


plugin_name = "鸡汤推送"
plugin_usage = '自动推送鸡汤，祝你每天都充满正能量\n自动推送开关为 鸡汤开|关'


JOBNAME = 'pcs'  # 任务id
CYCLE = 100  # 任务周期 分钟
VARIATION = 1200  # 推送时间随机度 秒


scheduler : BaseScheduler = require('nonebot_plugin_apscheduler').scheduler
pushdu = MatcherGroup(type='message', permission=GROUP)


async def push_poisonous_chicken_soup(gid: int): 
    bot : Bot = choice(show_gb_dict()[gid])

    try:
        with QbotDB() as qb:
            result = qb.queryone("SELECT sentence FROM dujitang JOIN (SELECT CEIL((SELECT MAX(id) FROM dujitang) * RAND()) AS id) AS r2 USING (id);")
        if not result:
            logger.error('Did not get record in mysql')
        else:
            logger.info(f'群 {gid} 当前由 {bot.self_id} 推送鸡汤')
            await bot.send_group_msg(group_id=gid, message=result[0])

    except ActionFailed as err:
        await bot.send_group_msg(group_id=gid, message='发送消息异常，疑似被风控')
        logger.error(f'failed to push message: {result[0]}')


du_groups_file = Path(__file__).parent/"dujitang_groups.json"

if not du_groups_file.exists():
    with du_groups_file.open('w', encoding='utf-8') as j:
        json.dump([], j)
with du_groups_file.open(encoding='utf-8') as j:
    du_groups = json.load(j)

for gid in du_groups:
    scheduler.add_job(push_poisonous_chicken_soup, 'interval', minutes=CYCLE, id=f"{JOBNAME}{gid}", jitter=VARIATION, misfire_grace_time=30, args=[gid])


def save_du_groups():
    """保存毒鸡汤群开启列表本地设置"""
    with du_groups_file.open('w', encoding='utf-8') as j:
        json.dump(du_groups, j)


# 7点-9点自动开启关闭
if datetime.now().hour < 7 or datetime.now().hour > 21:
    for job in scheduler.get_jobs():
        if job.id.startswith(JOBNAME):
            job.pause()
    logger.info('不在鸡汤推送时间段内，暂停任务')


@scheduler.scheduled_job('cron', hour=7, misfire_grace_time=120)
async def auto_start():
    for job in scheduler.get_jobs():
        if job.id.startswith(JOBNAME):
            job.resume()
    logger.info('进入鸡汤时间')
    # else:
    #     logger.info('鸡汤不在任务列表中，忽略自动启动')


@scheduler.scheduled_job('cron', hour=21, misfire_grace_time=120)
async def auto_pause():
    for job in scheduler.get_jobs():
        if job.id.startswith(JOBNAME):
            job.pause()
    logger.info('结束今日鸡汤')


du_on = pushdu.on_command('鸡汤开')
du_off = pushdu.on_command('鸡汤关')


@du_on.handle()
async def start_du(bot: Bot, event: GroupMessageEvent):
    gid = event.group_id
    job = scheduler.get_job(f"{JOBNAME}{gid}")

    if job:
        await du_on.finish('毒鸡汤已在推送列表中')
    job = scheduler.add_job(push_poisonous_chicken_soup, 'interval', minutes=CYCLE, id=f"{JOBNAME}{gid}", jitter=VARIATION, misfire_grace_time=30, args=[gid])
    du_groups.append(gid)
    save_du_groups()
    await du_on.send('好的，我要开始讲鸡汤啦')
    if datetime.now().hour < 7 or datetime.now().hour >= 21:
        job.pause()
        await asleep(1.5)
        await du_on.finish('emm, 但是今天太晚了，明天再讲吧')


@du_off.handle()
async def stop_du(bot: Bot, event: GroupMessageEvent):
    gid = event.group_id
    job = scheduler.get_job(f"{JOBNAME}{gid}")
    if not job:
        await du_off.finish('毒鸡汤不在推送列表中')
    scheduler.remove_job(f"{JOBNAME}{gid}")
    du_groups.remove(gid)
    save_du_groups()
    await du_off.finish('好了好了，不讲鸡汤了')