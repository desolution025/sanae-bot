'''
没什么特别的用处，从此处导入bot名字和超级用户方便替换而已
与bot.config.superusers区别为分别是int与str列表
注意permission中SUPERUSER是单数不带S
SUPERUSERS: Sequence[int]
BOTNAME: str
'''


from pathlib import Path
from pydantic import BaseSettings, validator
from typing import Optional, Sequence

from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.cqhttp.message import Message, MessageSegment
from nonebot.typing import T_State


class EnvSetting(BaseSettings):
    ENVIRONMENT: Optional[str] = None

    @validator('ENVIRONMENT')
    def verify_exsits(cls, v):
        real_env_file = cls.Config.env_file.parent/f".env.{v}"
        if not real_env_file.exists():
            raise FileNotFoundError(f'The indicated environment file was not found: {real_env_file.name}')
        return v

    class Config:
        env_file = Path.cwd()/'.env'


class EasySetting(BaseSettings):
    superusers: Sequence[int]
    nickname: Optional[Sequence[str]]
    debug: bool
    cancel_expression: Sequence[str]
    meitupath: str
    setupath: str

    class Config:
        env_file = Path.cwd()/f".env.{EnvSetting().ENVIRONMENT}"
        env_file_encoding = 'utf-8'


easy_setting = EasySetting()

SUPERUSERS = easy_setting.superusers
BOTNAMES = easy_setting.nickname
BOTNAME = easy_setting.nickname[0]
DEBUG = easy_setting.debug
CANCEL_EXPRESSION = easy_setting.cancel_expression
MEITUPATH = easy_setting.meitupath
SETUPATH = easy_setting.setupath


if __name__ == "__main__":
    print(SUPERUSERS, BOTNAME, DEBUG, MEITUPATH, SETUPATH)