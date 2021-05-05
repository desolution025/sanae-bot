from nonebot import on_command
from nonebot.rule import to_me

from nonebot_adapter_gocq.bot import Bot
from nonebot_adapter_gocq.event import MessageEvent as Event
from nonebot.typing import T_State
from nonebot.permission import SUPERUSER
from nonebot_adapter_gocq.permission import GROUP_OWNER

from src.common.log import logger
from src.common.verify import User_Blocker
from src.common.easy_setting import SUPERUSERS, BOTNAME


_plugin_name = '添加黑名单'


_plugin_usage = f'如果不想要让{BOTNAME}回复您的任何消息的话可以at我发送[屏蔽我]，{BOTNAME}即会忽略您的任何消息\n(当然不是加入黑名单，只是不响应你的消息)'


# 由维护组主动将用户加入黑名单
add_black_by_spuser = on_command('加入黑名单', aliases={'add_black'}, rule=to_me(), permission=SUPERUSER)

@add_black_by_spuser.handle()
async def abbs_1st_parse(bot: Bot, event: Event, state: T_State):
    bid = event.get_message().extract_plain_text().strip()
    if bid:
        if bid.isdigit():
            state['bid'] = bid  # 不要转数字，在下一个处理函数中统一转数字
        else:
            await add_black_by_spuser.send('不可识别的参数，请输入数字QQ账号')
    

@add_black_by_spuser.got('bid', prompt='输入要加入黑名单的账号，输入"取消"退出会话')
async def abbs_2nd_parse(bot: Bot, event: Event, state: T_State):
    bid = state['bid']
    if str(event.get_message()) == "取消":
        await add_black_by_spuser.finish('已取消当前对话')
    if not bid.isdigit():
        await add_black_by_spuser.reject('格式不正确，请输入数字QQ账号，输入"取消"退出对话')
    additonal_info = ''
    if bid in User_Blocker.block_list:
        additonal_info = '\n(该用户已在阻塞列表中，若添加黑名单将覆盖现有信息)'
    bid = int(bid)
    nickname = (await bot.get_stranger_info(user_id=bid))["nickname"]
    if nickname:
        await add_black_by_spuser.pause(f'获取到昵称为<{nickname}>的用户，是否将此用户加入黑名单？y/n' + additonal_info)
    else:
        await add_black_by_spuser.pause('获取到用户未设置昵称，请先检查qq号是否准确然后确认加入黑名单 y/n' + additonal_info)


@add_black_by_spuser.handle()
async def abbs_confirmation_handle(bot: Bot, event: Event, state: T_State):
    bid = state['bid']
    if str(event.get_message()) in ('y', 'Y', '是'):
        User_Blocker(bid).add_block(0)
        await add_black_by_spuser.finish(f'已将账户为 {bid} 的用户加入黑名单')
    elif str(event.get_message()) in ('n', 'N', '否'):
        await add_black_by_spuser.finish('已取消对该用户的操作')
    else:
        await add_black_by_spuser.finish('不符合预期的输入，将不处理本次操作')


# 用户主动将自己加入屏蔽列表
add_black_by_user = on_command('屏蔽我', rule=to_me())

@add_black_by_user.handle()
async def abbo_1st_parse(bot: Bot, event: Event, state: T_State):
    await add_black_by_spuser.send('调用该命令后我将不再响应任何与你有关的输入信息，且不可主动解除屏蔽\n输入"确认"即可生效')

@add_black_by_user.receive()
async def abbo_confirmation_handle(bot: Bot, event: Event):
    if event.raw_message.strip() == '确认':
        uid = event.get_user_id()
        User_Blocker(uid).add_block(1)
        logger.info(f'将用户 {uid} 加入屏蔽列表，reason：1')
        await add_black_by_user.finish('好的，我不会再响应您的消息~')
    else:
        await add_black_by_user.finish('未输入确认信息，我仍然会响应您的消息~')


# 辱骂屏蔽
BANNED_WORD = {
    'rbq', 'RBQ', '憨批', '废物', '死妈', '崽种', '傻逼', '傻逼玩意',
    '没用东西', '傻B', '傻b', 'SB', 'sb', '煞笔', 'cnm', '爬', '垃圾',
    'nmsl', 'D区', '口区', '我是你爹', 'nmbiss', '弱智', '给爷爬', '杂种爬','爪巴'
}


anti_abuse = on_command('SB', aliases=BANNED_WORD, rule=to_me())


@anti_abuse.handle()
async def ban_user(bot: Bot, event: Event):
    user_id = event.user_id
    if user_id in SUPERUSERS:
        await anti_abuse.finish('啊！你不可以这样说我！')
    else:
        User_Blocker(user_id).add_block(2)
        logger.info(f'因消息 "{event.raw_message}" 将用户 {user_id} 加入屏蔽列表，reason：2')
        await anti_abuse.finish('早苗好伤心！暂时不要理你了（╯°□°）╯︵( .o.)')


# TODO：群主加入黑名单权限，输入群号和群成员，然后验证群主身份与成员
# TODO：群内检测滥用屏蔽