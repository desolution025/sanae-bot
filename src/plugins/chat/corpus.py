from typing import Union, Literal, List, Tuple
from random import choice
from src.common.dbpool import QbotDB
from src.common.log import logger


def query(question: str, gid: int, q: bool=False) -> List[Tuple]:
    """以问句查询语料库

    返回ID，回答，出现率三个数据组成的元组的列表，不会包含出现率为0以及不在此群创建的非公开的记录
    以完全模式查询时返回ID，回答，出现率，创建者，来源，创建时间，公开性七个数据组成的元组的列表，并且不过滤除问句之外的任何条件

    Args:
        question (str): 要查询的问句
        gid (int): 在哪个群发出的查询命令，私聊时应为0
        q (bool, optional): 完全查询模式. Defaults to False.

    Returns:
        List[Tuple]: 返回结果为列表
    """
    with QbotDB() as qb:
        if not q:
            cmd = 'SELECT ID, answer, probability FROM corpus WHERE probability > 0 AND question=%s AND NOT (public=0 AND source!=%s);'
            param = (question, gid)
            result = qb.queryall(cmd, param)
        else:
            cmd = 'SELECT ID, answer, probability, creator, source, creation_time, public FROM corpus WHERE question=%s;'
            param = (question,)
            result = qb.queryall(cmd, param)
    return result


def query_exists(sid: int) -> List[Tuple[Literal[1]]]:
    """以对话ID查询记录是否存在, 返回没有实质意义的列表"""
    with QbotDB() as qb:
        return qb.queryone('SELECT 1 FROM corpus WHERE ID=%s LIMIT 1;', (sid,))


def plus_one(sid: int, plus_num: int=1):
    """指定ID的记录call_times加一"""
    
    with QbotDB() as qb:
        cmd = 'UPDATE corpus SET call_times=call_times+%s WHERE ID=%s;'
        param = (plus_num, sid)
        qb.update(cmd, param)
    logger.debug(f'SID {sid}: call_times + {plus_num}')