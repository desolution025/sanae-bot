from nonebot.plugin import on_notice
from nonebot.adapters.cqhttp.event import GroupBanNoticeEvent
# from nonebot_adapter_gocq.event import GroupBanNoticeEvent
from src.common import T_State, BOTNAME, Bot
from src.common.rules import sv_sw, comman_rule
# from nonebot_adapter_gocq.bot import Bot


async def didiban(bot: Bot, event: GroupBanNoticeEvent, state: T_State):
    selfinfo = await bot.get_group_member_info(group_id=event.group_id)
    if selfinfo["role"] == "admin" and event.group_id == 973573381 and event.operator_id == 3548597378:
        state["uid"] = event.user_id
        return True


antididi = on_notice(rule=sv_sw('抗蒂蒂')&comman_rule(GroupBanNoticeEvent)&didiban)


@antididi.handle()
async def unban(bot: Bot, event: GroupBanNoticeEvent, state: T_State):
    try:
        await bot.set_group_ban(group_id=event.group_id, user_id=state["uid"], duration=0)
        await antididi.finish('Poor man, 苗苗会拯救不知道有没有罪的你')
    except:
        await antididi.finish('要是苗苗有力量的话...就可以拯救你了..岂可修！')
    