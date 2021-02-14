from pathlib import Path
from nonebot.log import logger


logfolder = Path('./log')
if not logfolder.exists():
    logfolder.mkdir()


logger.add(logfolder/"{time:YYYY-MM-DD}.log", rotation="00:00", retention="1 days", encoding='utf-8')


if __name__ == "__main__":
    logger.info('编码测试')