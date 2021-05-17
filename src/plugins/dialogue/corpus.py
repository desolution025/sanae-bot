from typing import Optional, Union, Literal, List, Tuple, Sequence
from datetime import datetime, timedelta
from random import choice

from src.common.dbpool import QbotDB
from src.common.log import logger


class Reply_Called:
    """记录群内触发过的对话id，超过30分钟清空数据，语句即可重复被调用"""

    def __init__(self, gid: int) -> None:
        self.gid = gid
        self.called = {0}  # 存储调用过的记录id，拥有有一个id0防止字符串化时单个元素的元组带有多余的逗号导致sql语法错误
        self.recording_time = datetime.now()

    def check_expired(self):
        if datetime.now() - self.recording_time > timedelta(minutes=10):
            self.recording_time = datetime.now()
            self.called = {0}


Called_Reply = {}  # 存储装有Reply_Called的实例


def query(question: str, gid: int, q: bool=False) -> Optional[List[Tuple]]:
    """以问句查询语料库

    返回ID，回答，出现率三个数据组成的元组的列表，不会包含出现率为0以及不在此群创建的非公开的记录
    以完全模式查询时返回ID，回答，出现率，创建者，来源，创建时间，公开性七个数据组成的元组的列表，并且不过滤除问句之外的任何条件

    Args:
        question (str): 要查询的问句
        gid (int): 在哪个群发出的查询命令，私聊时应为0
        q (bool, optional): 完全查询模式. Defaults to False.

    Returns:
        Optional[List[Tuple]]: 返回结果为列表
    """
    with QbotDB() as qb:
        if not q:
            cmd = 'SELECT ID, answer, probability FROM corpus WHERE probability > 0 AND question=%s AND NOT (public=0 AND source!=%s)'
            # 如果gid是0就是私聊，不会附加过滤重复度的条件
            if gid:
                if gid not in Called_Reply:
                    Called_Reply[gid] = Reply_Called(gid)
                if len(Called_Reply[gid].called) > 1:
                    cmd += f' AND id NOT IN {tuple(Called_Reply[gid].called)};'
                else:
                    cmd += ';'
            else:
                cmd += ';'
            param = (question, gid)
            result = qb.queryall(cmd, param)
        else:
            cmd = 'SELECT ID, answer, probability, creator, source, creation_time, public FROM corpus WHERE question=%s;'
            param = (question,)
            result = qb.queryall(cmd, param)
    return result


def query_exists(sid: int, q: bool=False) -> List[Tuple[Literal[1]]]:
    """以对话ID查询记录是否存在, 返回没有实质意义的列表
    
    查询模式(q)下返回的创建者、创建地点、公开性信息"""
    with QbotDB() as qb:
        if not q:
            return qb.queryone('SELECT 1 FROM corpus WHERE ID=%s LIMIT 1;', (sid,))
        else:
            return qb.queryone('SELECT creator, source, public FROM corpus WHERE ID=%s LIMIT 1;', (sid,))


def plus_one(sid: int, gid: int, plus_num: int=1):
    """指定ID的记录call_times加一"""
    
    with QbotDB() as qb:
        cmd = 'UPDATE corpus SET call_times=call_times+%s WHERE ID=%s;'
        param = (plus_num, sid)
        qb.update(cmd, param)
    if gid:
        his = Called_Reply[gid]
        his.called.add(sid)
        his.check_expired()
    logger.debug(f'SID {sid}: call_times + {plus_num}')


def insertone(question: str, answer: str, probability: int, creator: int, source: int, public: Literal[0, 1]) -> Union[int, Tuple[int, datetime]]:
    """向数据库插入对话
    
    如果对话已存在并且是公开对话或非公开对话且来源一致则不插入，返回已存在的对话信息
    否则会插入记录并返回最新插入的记录的id

    ※使用返回值数据类型判断是否成功插入

    Args:
        question (str): 问句
        answer (str): 回答
        probability (int): 相对出现率 0-100
        creator (int): 创建者ID
        source (int): 创建地点
        public Literal[0, 1]): 公开性 0或1

    Returns:
        Union[int, Tuple[int, datetime]]: 刚插入记录的id，如果对话已存在则返回对话的信息
    """
    
    with QbotDB() as qb:
        # 插入单个
        if public == 1:
            querycmd = 'SELECT creator, creation_time FROM corpus WHERE question=%s AND answer=%s AND public=1 LIMIT 1;'
            queryparam = (question, answer)
        else:
            querycmd = 'SELECT creator, creation_time FROM corpus WHERE question=%s AND answer=%s AND public=0 AND source=%s LIMIT 1;'
            queryparam = (question, answer, source)
        result = qb.queryone(querycmd, queryparam)
        if result:
            return result  # 返回单个重复数据，tuple
        else:
            qb.insert('INSERT INTO corpus (question, answer, probability, creator, source, public, creation_time, call_times) VALUES (%s, %s, %s, %s, %s, %s, NOW(), 0)',
            (question, answer, probability, creator, source, public))
        # 返回最后插入的id
        last = qb.queryone('SELECT LAST_INSERT_ID();')
        return last[0]


def insertmany(question: Sequence[str], answer: Sequence[str], probability: int, creator: int, source: int, public: Literal[0, 1]) -> Union[int, List[Tuple[str, str, int, datetime]]]:
    """向数据库插入多条对话
    
    如果对话已存在并且是公开对话或非公开对话且来源一致则不插入，返回已存在的对话信息
    否则会插入记录并返回最新插入的最小、最大id组成的tuple

    ※使用返回值数据类型判断是否成功插入

    Args:
        question (Sequence[str]): 问句队列
        answer (Sequence[str]): 回答队列
        probability (int): 相对出现率 0-100
        creator (int): 创建者ID
        source (int): 创建地点
        public (Literal[0, 1]): 公开性 0或1

    Returns:
        Union[int, List[Tuple[str, str, int, datetime]]]: 成功则返回插入的数量，有重复的则返回重复的数据
    """

    if len(question) == 1:
        questions = f'("{question[0]}")'
    else:
        questions = tuple(question)
    if len(answer) == 1:
        answers = f'("{answer[0]}")'
    else:
        answers = tuple(answer)

    with QbotDB() as qb:
        if public == 1:
            querycmd = f'SELECT question, answer, creator, creation_time FROM corpus WHERE question in {questions} AND answer in {answers} AND public=1;'
            queryparam = ()
        else:
            querycmd = f'SELECT question, answer creator, creation_time FROM corpus WHERE question in {questions} AND answer in {answers} AND public=0 AND source=%s;'
            queryparam = (source,)
        result = qb.queryall(querycmd, queryparam)
        if result:
            # TODO: 把重复的数据过滤出去，剩余的插入记录
            return result  # 返回所有重复数据，list
        else:
            qb.insertmany('INSERT INTO corpus (question, answer, probability, creator, source, public, creation_time, call_times) VALUES (%s, %s, %s, %s, %s, %s, NOW(), 0) ON DUPLICATE KEY UPDATE creation_time=NOW();',
            [(q, a, probability, creator, source, public) for q in question for a in answer])
        # 返回最后插入的最小id和最大id
        last = qb.queryone('SELECT LAST_INSERT_ID();')
        # return last[0][0], len(question) * len(answer) + last[0][0]
    return len(question) * len(answer)  # 返回插入的数量，如果有需求对最后插入的数据做处理再用上面那个

    
def update_prob(sid: Union[int, Tuple[int, int]], prob: int):
    """更新出现率

    Args:
        sid (Union[int, Tuple[int, int]]): 对话id，若要更新多个则传入最小id和最id组成的数组
        prob (int): 更新后的出现率
    """
    if prob < 0 or prob > 100:
        logger.error(f'Probability {prob} out of range!')
        return
    with QbotDB() as qb:
        if isinstance(sid, int):
            qb.update('UPDATE corpus SET probability=%s WHERE id=%s;', (prob, sid))
        else:
            min_, max_ = sid
            qb.update(f'UPDATE corpus SET probability=%s WHERE id BETWEEN %s AND %s;', (prob, min_, max_))


def del_record(sid: int):
    """删除记录"""
    with QbotDB() as qb:
        qb.delete('DELETE FROM corpus WHERE ID=%s;', (sid,))