from src.common.dbpool import QbotDB


def query_fortune(uid: int):
    with QbotDB() as qb:
        cmd = 'SELECT  运势, 运势_day FROM call_times WHERE qq_number=%s'
        result = qb.queryone(cmd, (uid,))
    return result


def draw_fortune(uid: int, stick):
    with QbotDB() as qb:
        cmd = 'UPDATE call_times SET 运势=%s WHERE qq_number=%s'
        qb.update(cmd, (stick, uid))