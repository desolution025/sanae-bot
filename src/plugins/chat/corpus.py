from random import choice
from src.common.dbpool import QbotDB


def query(question: str):
    with QbotDB() as qb:
        cmd = 'SELECT answer, public FROM corpus WHERE question=%s;'
        param = (question,)
        result = qb.queryall(cmd, param)
    if result:
        return choice(result)[0]