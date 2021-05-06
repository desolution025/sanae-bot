from nonebot.plugin import on_request
from nonebot_adapter_gocq.event import FriendRequestEvent

from src.common import Bot, FRIENDREQUESTCODESALT, SUPERUSERS
from src.common.rules import comman_rule
from src.common.levelsystem import UserLevel
from src.utils import get_hash_code


_plugin_name = '处理好友请求'


friend_request = on_request(rule=comman_rule(FriendRequestEvent))


@friend_request.handle()
async def virify_request(bot: Bot, event: FriendRequestEvent):
    if event.comment == get_hash_code(FRIENDREQUESTCODESALT, event.user_id) and UserLevel(event.user_id).level > 3:
        await event.approve()
        for sps in SUPERUSERS:
            await bot.send_private_msg(user_id=sps, message=f'用户 {event.user_id} 通过了好友验证，已添加好友')
    else:
        await bot.set_friend_add_request(flag=event.flag, approve=False)