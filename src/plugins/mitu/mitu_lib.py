from datetime import datetime, timedelta
from pathlib import Path
import glob

from emoji import emojize, demojize

from src.common.dbpool import GalleryDB
from src.common.log import logger
from src.common.easy_setting import MEITUPATH


class Group_Called:
    """用于记录群内已经调用过的图片id，超过两小时会清空数据重新记录
    """

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


Called_Data = {}  # 存储装有Group_Called的实例


def get_mitu(gid: int, kwd: tuple=(), num: int=1, min_sl: int=0, max_sl: int=1):
    """从数据库中获得美图数据

    Args:
        gid (int): 呼叫美图的群号，相同群内会有两个小时的记录去重
        kwd (tuple, optional): 关键词，元组内的词会做交集查询. Defaults to ().
        num (int, optional): 查询数量. Defaults to 1.
        min_sl (int, optional): 最小的sl值. Defaults to 0.
        max_sl (int, optional): 最大的sl值. Defaults to 1.

    Returns:
        tuple: 返回是否调用成功以及返回的结果，如果没有查询结果会返回无结果还是结果已经用尽，如果有结果会返回数据列表
        数据结构：{
                'title' (str): 作品名,
                'author' (str): 作者,
                'source' (str): 来源, Pixiv pid_p
                'sl' (int): sl级别,
                'file' (int): 文件路径
                }
    """
    if gid not in Called_Data:
        Called_Data[gid] = Group_Called(gid)
    his = Called_Data[gid]
    kwds = "%" + '%'.join(kwd) + "%"  # like查询要在两边加上%占位符
    kwds_demojize = demojize(kwds)  # 查询数据库要用转义为普通字符的emoji
    with GalleryDB() as glrdb:
        # TODO: 优化随机查询的方式取代orded by rand()
        if len(his.called) > 1:
            cmd = f'''select title, author, source, sl, visits, id from gallery
            where sl between %s and %s and id not in {tuple(his.called)}
            and (tags like %s or title like %s or author like %s)
            ORDER BY RAND() LIMIT %s;'''
        else:
            cmd = '''select title, author, source, sl, visits, id from gallery
            where sl between %s and %s and (tags like %s or title like %s or author like %s)
            ORDER BY RAND() LIMIT %s;'''
        params = (min_sl, max_sl, kwds_demojize, kwds_demojize, kwds_demojize, num)
        results = glrdb.queryall(cmd, params)
        # 随机查询不在called列表中的图片
        if not results:
            if kwds in his.called_kwds:
                return False, f'暂时没有更多关于"{kwds.replace("%", "|")[1:-1]}"的美图了'
            else:
                return False, f'没有找到关于"{kwds.replace("%", "|")[1:-1]}"的美图'  # TODO: 换了标签之后再搜索到相同的图用这个标签不太合适，换成"有x张相关图刚才已经发过了"
        mitu_ls = []  # 所有美图列表
        for record in results:
            if record[2].startswith('Pixiv'):  # 暂时只有pixiv图片，加入非p站图片之后要增加拼装文件名方法
                filestem = record[2][6:]  # 名字是去掉Pixiv 前缀剩下的pid_p
            searchfile = glob.glob(str(Path(MEITUPATH)/('sl' + str(record[3]))/(filestem)) + '.[jp][pn]*g')  # 从本地图库中搜索图片,暂时只搜索jpg, png, jpeg，正常情况应该只能搜到一个
        
            if not searchfile:
                logger.error(f'Not found file {filestem}')
                mitu_ls.append(None)
                continue
            elif len(searchfile) > 1:
                logger.warning(f'查找到多个名称为{filestem}的图片，请检查图库')
            logger.debug(f'Found {len(searchfile)} file(s)：' + '\n'.join(searchfile))
            data = {
                'title': emojize(record[0]),
                'author': emojize(record[1]),
                'source': record[2],
                'sl': record[4],
                'file': searchfile[0]
                }
            mitu_ls.append(data)

            his.called.add(record[5])  # 添加id记录
            

        his.called_kwds.add(kwds)  # 添加关键词记录
        his.check_expired()  # 检查记录是否过期
        if len(results) == 1:
            increase_cmd = "UPDATE gallery SET visits=visits+1 WHERE id=%s;"
            increase_parm = (results[0][5],)
        else:
            id_ls = str(tuple([r[5] for r in results]))  # 如果有多条记录就传入元组同时加1
            increase_cmd = f"UPDATE gallery SET visits=visits+1 WHERE id in {id_ls};"
            increase_parm = ()
        glrdb.update(increase_cmd, increase_parm)  # 调用次数加一

        return True, mitu_ls