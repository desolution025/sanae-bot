from typing import Sequence, Union, Literal, List
from datetime import datetime, timedelta
from pathlib import Path
import requests

from src.common import SETUPATH, logger
from src.common.dbpool import GalleryDB
from src.utils import concat_seq


class Setu_Called:
    """用于记录群内已经调用过的图片id，超过两小时会清空数据重新记录"""

    def __init__(self, gid: int) -> None:
        self.gid = gid
        self.called = {0}  # 存储调用过的图片id, 永远有一个id0在里面防止字符串化时单个元素的元组带有多余的逗号导致sql语法错误
        self.called_kwds = set()  # 存储调用过的关键词，通过这个来判断是不存在相关图片还是相关图片已全部调用完
        self.recording_time = datetime.now()

    def check_expired(self):
        if datetime.now() - self.recording_time > timedelta(hours=2):
            self.recording_time = datetime.now()
            self.called = {0}
            self.called_kwds.clear()


Setu_Called_Data = {}  # 存储装有Setu_Called的实例


def get_setu(gid: int, kwds: Sequence[str], num: int=1, r18: int=0):
    """从数据库中获得色图数据

    Args:
        gid (int): 呼叫色图的群号，相同群内会有两个小时的记录去重，私聊传入0以不做处理
        kwd (tuple): 关键词，元组内的词会做交集查询
        num (int, optional): 查询数量. Defaults to 1.
        r18 (int, optional): 是否包含r18图片，0：没有R18，1：只有R18，2：混合. Defaults to 0.

    Returns:
        tuple: 返回是否调用成功以及返回的结果，如果没有查询结果会返回无结果还是结果已经用尽，如果有结果会返回数据列表
        数据结构：{
                'count' (int): 返回数量，为了与lolicon结构保持一致,
                'data' (list):{
                    'title' (str): 作品名,
                    'author' (str): 作者,
                    'source' (str): pid_p,
                    'file' (Path): 文件路径
                    }
                }
    """
    if gid:
        if gid not in Setu_Called_Data:
            Setu_Called_Data[gid] = Setu_Called(gid)
        his = Setu_Called_Data[gid]
    
    with GalleryDB() as glrdb:
        # TODO: 优化随机查询的方式取代orded by rand()
        cmd = 'SELECT pid, p, title, author, url, id FROM lolicon WHERE '
        if r18 != 2:
            cmd += f'r18={r18} AND '
        # 过滤已经调用过的图片
        if gid and len(his.called) > 1:
            cmd += f'id NOT IN {tuple(his.called)} AND '
        # 添加关键词条件并随机抽取
        cmd += ' AND '.join(['(tags LIKE %s OR title LIKE %s OR author LIKE %s)'] * len(kwds))
        cmd += ' ORDER BY RAND() LIMIT %s'
        # 三个一组的关键词参数与一个limit参数
        params = concat_seq(*[(k, k, k) for k in map(lambda x: '%' + x + '%', kwds)]) + (num,)
        logger.debug(f'执行SQL>>{cmd}'%params)
        # logger.debug(f'执行SQL>>{cmd}')
        # logger.debug(f'{params=}')

        results = glrdb.queryall(cmd, params)

        if not results:
            if gid and kwds in his.called_kwds:
                return False, f'暂时没有更多关于"{"|".join(kwds)}"的涩图了'
            else:
                return False, f'没有找到关于"{"|".join(kwds)}"的涩图'  # TODO: 换了标签之后再搜索到相同的图用这个标签不太合适，换成"有x张相关图刚才已经发过了"
        setu_ls = []  # 所有色图列表
        for record in results:

            filestem = str(record[0]) + '_p' + str(record[1])  # 名字是pid_p
            suffix : str = record[4].split('.')[-1]  # 后缀从url里解析
            filename = filestem + '.' + suffix
            filepath = Path(SETUPATH)/filename
            logger.debug(f'定位本地文件{filepath}')
            if not filepath.exists():
                logger.warning(f'Did not found local file [{filename}]')
                try:
                    r = requests.get(record[4])
                    filepath.write_bytes(r.content)
                    logger.info(f'Downloaded file [{filename}] into setupath')
                except Exception as err:
                    logger.exception(f'Failed to download file [{filename}]: {err}')
                    setu_ls.append(None)
                    continue

            data = {
                'title': record[2],
                'author': record[3],
                'source': filestem,
                'file': filepath
                }
            setu_ls.append(data)
            if gid:
                his.called.add(record[5])  # 添加id记录
        if gid:
            his.called_kwds.add(kwds)  # 添加关键词记录
            his.check_expired()  # 检查记录是否过期

        return True, {'count': len(setu_ls), 'data': setu_ls}


def increase_setu(pid: int, p: int, uid: int, title: str, author: str, url: str, r18: Union[bool, Literal[0, 1]], tags: List[str]):
    """插入一条lolicon的图片信息"""
    with GalleryDB() as glrdb:
        qcmd = 'SELECT 1 FROM lolicon WHERE pid=%s AND p=%s LIMIT 1;'
        qparams = (pid, p)
        if glrdb.queryone(qcmd, qparams):
            logger.warning(f"Record [{str(pid) + '_' + str(p)}] has exists")
        else:
            cmd = "INSERT INTO lolicon (pid, p, uid, title, author, url, r18, tags) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"
            params = (pid, p, uid, title, author, url, r18, ','.join(tags))
            glrdb.insert(cmd, params)
            logger.info(f"Insert one record into lolicon: {str(pid) + '_' + str(p)}")
