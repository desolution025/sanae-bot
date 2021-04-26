from typing import Optional
from src.common.dbpool import QbotDB


def query_fortune(uid: int) -> Optional[str]:
    with QbotDB() as qb:
        cmd = 'SELECT  运势 FROM calltimes WHERE qq_number=%s'
        result = qb.queryone(cmd, (uid,))
    return result[0]


def draw_fortune(uid: int, stick):
    with QbotDB() as qb:
        cmd = 'UPDATE calltimes SET 运势=%s WHERE qq_number=%s'
        qb.update(cmd, (stick, uid))