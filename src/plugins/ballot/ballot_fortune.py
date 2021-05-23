from typing import Optional
from src.common.dbpool import QbotDB
from src.common import logger


def query_fortune(uid: int) -> Optional[str]:
    with QbotDB() as qb:
        cmd = 'SELECT  运势 FROM calltimes WHERE qq_number=%s'
        result = qb.queryone(cmd, (uid,))
        if not result:
            logger.error(f'Failed to get calltimes info of user：{uid}')
            return None
    return result[0]


def draw_fortune(uid: int, stick):
    with QbotDB() as qb:
        cmd = 'UPDATE calltimes SET 运势=%s WHERE qq_number=%s'
        qb.update(cmd, (stick, uid))


def get_active_user(*uids, num: int=5):
    """获得最近签到过的num个群员，uids通常应该是过滤过的本群bot使用用户"""
    
    with QbotDB() as qb:
        result = qb.queryall(f'SELECT qq_number FROM userinfo where qq_number in {tuple(uids)} ORDER BY last_sign DESC LIMIT %s;', (num,))
    return [q[0] for q in result]