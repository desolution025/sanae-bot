from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event
from src.plugins.botmanage.verify import Group_Blocker
from src.common.easy_setting import BOTNAME, SUPERUSERS


plugin_name = '全局开关'


turn_on = on_command('on', aliases={'启动', 'ON'}, rule=to_me(), permission=GROUP)

@turn_on.handle()
async def turnon(bot: Bot, event: Event):
    sender = event.sender
    if sender.role in ('owner', 'admin') or sender.user_id in SUPERUSERS:
        blocker = Group_Blocker(event.group_id)
        if blocker.check_block():
            await turn_on.finish(f'{BOTNAME}没有离开哦，一直在哦~')
        elif blocker.turn_on():  # 使用这个查询的时候就直接打开了
            await turn_on.finish(f'{BOTNAME}回来啦~我不在的这段时间你们又和那个野女人发生了什么Ծ‸Ծ')
        else:
            await turn_on.finish(f'因为一些原因{BOTNAME}不能在此群发言。。。啊，不小心说出来了')


turn_off = on_command('off', aliases={'回避', 'OFF'}, rule=to_me(), permission=GROUP)
        
@turn_off.handle()
async def turnoff(bot: Bot, event: Event):
    sender = event.sender
    if sender.role in ('owner', 'admin') or sender.user_id in SUPERUSERS:
        blocker = Group_Blocker(event.group_id)
        if blocker.check_block():
            blocker.add_block(3)
            await turn_off.finish(f'啊，是要和群员做什么羞羞的事吗(⁄ ⁄•⁄ω⁄•⁄ ⁄)，那么{BOTNAME}先回避了~')
        else:
            await turn_off.finish('已经关了')
    else:
        await turn_off.finish('请联系管理员关闭我吧~')