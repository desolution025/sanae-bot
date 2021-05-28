from pathlib import Path
from random import choice, randint
from asyncio import sleep as asleep

from nonebot.plugin import on_message
from nonebot_adapter_gocq.exception import ActionFailed

from src.common import Bot, MessageEvent, logger, BOTNAME, MessageSegment, RESPATH
from src.common.rules import sv_sw, full_match
from src.common.levelsystem import UserLevel, is_user, filter_users
from src.utils import imgseg, DailyNumberLimiter
from .ballot_fortune import query_fortune, draw_fortune, get_active_user


plugin_name = '运势'
plugin_usage = """[今日运势] 没日一抽，运气好的话当天可能出门被撞到异世界当美少女"""


assets_folder = Path(RESPATH)/'fortune'
sticks = [i for i in  assets_folder.glob('*.[jp][pn]*g')]


fortune = on_message(rule=sv_sw(plugin_name, plugin_usage)&full_match(('运势', '今日运势')), priority=2)


@fortune.handle()
async def check_fortune(bot: Bot, event: MessageEvent):
    name = event.sender.card if event.message_type == 'group' else event.sender.nickname
    dlmt = DailyNumberLimiter(event.user_id, func_name='运势', max_num=1)
    stick = query_fortune(event.user_id)
    rp = 0  # 如果抽中了特殊的签要发生一些事件 TODO：加入一些今天功能冷却减少之类的什么奖励吧
    if dlmt.check(close_conn=False) or not stick:
        stick = choice(sticks)
        if dlmt.count == 0:
            if stick.name == '28.jpg':  # 恋爱运，惩罚
                rp = 1
            elif stick.name == '27.jpg':  # 凶，奖励
                rp = 2
            elif stick.name in ('8.jpg', '16.jpg', '19.jpg'):  # 金运，给钱
                rp = 3
            elif stick.name in ('15.jpg', '23.jpg'):  # 全体运，群内统统滴奖励，私聊无效
                rp = 4
            elif stick.name == '17.jpg':  # 关系运， 私聊的时候给予奖励吧
                rp = 5

        draw_fortune(event.user_id, stick.name)
        dlmt.increase()
    else:
        dlmt.conn.close()
        stick = assets_folder/stick
    logger.debug(f'{event.user_id} got stick {stick.name}')
    await fortune.send(f'{name}今日的运势是' + imgseg(stick), at_sender=True)

    if rp:
        await asleep(1.5)
        if event.message_type == 'group':
            name = event.sender.card or event.sender.nickname or event.get_user_id()
        else:
            name = event.sender.nickname or event.get_user_id()

        if rp == 1 and is_user(event.user_id):
            exp = randint(9, 15)
            fund = randint(20, 30)
            user = UserLevel(event.user_id)
            await user.expup(-exp, bot, event)
            user.turnover(-fund, check_overdraft=False)
            await fortune.finish(f'虽然你抽中了恋爱运也不一定会遇到恋爱事件，不过对和恋爱沾边的家伙给予惩罚才是正义的\n{name}的exp -{exp}, 资金 -{fund}', at_sender=True)

        elif rp == 2 and is_user(event.user_id):
            exp = randint(15, 25)
            fund = randint(30, 50)
            user = UserLevel(event.user_id)
            await user.expup(exp, bot, event)
            user.turnover(fund)
            await fortune.finish('Emmmm，因为占卜的师傅如果不是有别的什么目的的话,为了讨好前来占卜的人都会尽量说是吉签嘛\n    抽到这个凶签这种小概率事件，某种意义上这才是奇迹真正应该有的样子'
            f'\n{name}获得了{exp}exp和{fund}资金', at_sender=True)

        elif rp == 3 and is_user(event.user_id):
            fund = randint(20, 30)
            user = UserLevel(event.user_id)
            user.turnover(fund)
            await fortune.finish(f'因为{BOTNAME}给不了你软妹币所以也只好送些这个给你了~不过说不定哪天它会像比特币一样突然价值激增哦~\n{name}获得了{fund}资金', at_sender=True)

        elif rp == 4:
            if event.message_type == 'group':

                await fortune.send('大家会感谢你的，无私的散财者~骗你的( •̀ ω •́ )✧', at_sender=True)
                memberlist = await bot.get_group_member_list(group_id=event.group_id)
                uids = filter_users(*[m['user_id'] for m in memberlist])
                if len(uids) > 5:
                    uids = get_active_user(*uids)
                logger.debug(f'获得奖励的群员{uids}')
                if uids:
                    for uid in uids:
                        exp = randint(5, 8)
                        fund = randint(5, 8)
                        user = UserLevel(uid)
                        await user.expup(exp, bot, event=None, gid=event.group_id)

                        try:
                            member = await bot.get_group_member_info(group_id=event.group_id, user_id=uid)
                        except ActionFailed as e:
                            logger.warning(f'可能是已经退群的群员: group: {event.group_id} qq: {uid}, error: {e}')
                            await fortune.send(group_id=event.group_id, message=f'本应该在群内的成员({uid})貌似获取不到了，是不是退群了呢？没有的话请联系维护组查看一下出问题的原因哦~')
                            continue

                        name = member['card'] or member['nickname'] or str(uid)
                        await fortune.send(message=MessageSegment.text(f'{name}获得了{exp}exp和{fund}资金') + MessageSegment.at(qq=uid))
                        await asleep(1.5)
                    
                else:
                    await fortune.finish('啊嘞，这个群里好像还没有能获得奖励的伙伴呢~')
            else:
                await fortune.finish('可惜这里是私聊所以全体运的效果生效不了了呢~')

        elif rp == 5 and is_user(event.user_id):
            if event.message_type == 'group':
                await fortune.finish('啊~获得了可以增加亲密度的签，但是这个签只有私聊抽中的时候才有效哦~残念', at_sender=True)
            else:
                exp = randint(25, 40)
                fund = randint(40, 50)
                user = UserLevel(event.user_id)
                await user.expup(exp, bot, event)
                user.turnover(fund)
                await fortune.finish(f'真的为了什么才和{BOTNAME}进行私密对话的吗？送你{exp}exp和{fund}资金吧，除了这些{BOTNAME}也没有其它的了')