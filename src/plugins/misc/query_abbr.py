import aiohttp
from nonebot.plugin import on_regex
from src.common import Bot, MessageEvent, T_State, logger
from src.common.rules import sv_sw


plugin_name = '查缩写'
plguin_usage = '''来源：能不能好好说话
链接：https://lab.magiconch.com/nbnhhsh/

[xxx是什么] 如果是字母缩写的话会返回缩写原意'''


async def get_sx(word):
    url = "https://lab.magiconch.com/api/nbnhhsh/guess"

    headers = {
        'origin': 'https://lab.magiconch.com',
        'referer': 'https://lab.magiconch.com/nbnhhsh/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
    }
    data = {
        "text": f"{word}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, headers=headers, data=data) as resp:
            msg = await resp.json()
            return msg if msg else []


sx = on_regex(r'([a-zA-Z]+)是(?:什么|啥)[?？]?$', rule=sv_sw(plugin_name, plguin_usage, hierarchy='其它'), priority=2)


@sx.handle()
async def sx_rev(bot: Bot, event: MessageEvent, state: T_State):
    logger.debug(f'Match sx {state["_matched_groups"]}')
    abbr = state["_matched_groups"][0]
    try:
        data = await get_sx(abbr)
    except aiohttp.ClientError as err:
        logger.error(f'query sx {abbr} error: {err}')
        await sx.finish("查询出错了，要不要稍后再试试？")
    try:
        name = data[0]['name']
        logger.debug(f'查询缩写：{name}')
        content = data[0]['trans']
        logger.debug(f'查找到的缩写：{content}')
        if len(content) == 0:
            await sx.finish(f'没有找到缩写可能为{name}的内容')
        msg = f'{name} 的意思可能为:'
        if len(content) > 1:
            msg += '\n'
        await sx.send(msg + "、".join(content))
    except:
        await sx.finish(f'没有找到缩写可能为{abbr}的内容')