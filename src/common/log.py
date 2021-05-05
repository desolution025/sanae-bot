"""
使用这个模块中的logger以自动记录日志到指定文件
"""


from pathlib import Path
from nonebot.log import logger
from .easy_setting import DEBUG


logfolder = Path('./logs')
if not logfolder.exists():
    logfolder.mkdir()


level = "DEBUG" if DEBUG else "WARNING"
logger.add(logfolder/"{time:YYYY-MM-DD}.log", rotation="00:00", retention="1 days", encoding='utf-8', level=level)


if __name__ == "__main__":
    logger.info('编码测试')