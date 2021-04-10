from pathlib import Path
import configparser
from pydantic import BaseModel
# from ipaddress import IPv4Address
from  mysql.connector import pooling, Error
try:
    from src.common.log import logger
except ImportError:
    from loguru import logger


# 数据库配置模型
class DBConfig(BaseModel):
    # host: IPv4Address  连接池传入IPV4地址不能自动转换str
    host: str
    port: int
    user: str
    password: str


cfg = configparser.ConfigParser()
cfg.read(Path(__file__).parent/"dbpool.ini")

dbcfg = DBConfig(**dict(cfg.items("client")))  # 数据库配置


class MysqlPool:
    """
    :Summary:

        mysql连接池的基类，使用时用子类继承的方法以在不同的子类属性中存储不同的数据库连接池实例
    
    :Args:
    
        ``db``: 要使用哪个数据库
        ``**kw``: 其他参数需要传输数据库配置信息及连接池配置信息
    """
    # 连接池名字对应连接池实例的字典
    _pool = None
    def __init__(self, db: str, **kw) -> None:
        if self.__class__._pool is None:
            self.__class__._pool = pooling.MySQLConnectionPool(db=db, **kw)
        self._conn = self.__class__._pool.get_connection()
        self.cursor = self._conn.cursor()
        self.q = True  # 查询模式，用来更新数据时自动调用commit

    def _execute(self, cmd, param=()):
        try:
            self.cursor.execute(cmd, param)
        except Error as e:
            logger.exception(e)

    def queryall(self, cmd, param=()):
        self._execute(cmd, param)
        return self.cursor.fetchall()
    
    def queryone(self, cmd, param=()):
        """
        ※除非能确定返回值只有一项否则调用此方法时命令要增加limit 1条件不然会触发Unread result found异常
        """
        self._execute(cmd, param)
        return self.cursor.fetchone()

    def querymany(self, cmd, num, param=()):
        self._execute(cmd, param)
        return self.cursor.fetchmany(num)

    def insert(self, cmd, param=()):
        self._execute(cmd, param)
        self.q = False

    def insertmany(self, cmd, values):
        self.cursor.executemany(cmd, values)
        self.q = False

    def update(self, cmd, param=()):
        self._execute(cmd, param)
        self.q = False

    def delete(self, cmd, param=()):
        self._execute(cmd, param)
        self.q = False

    def begin(self):
        """
        @summary: 开启事务
        """
        self._conn.begin()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self.cursor.close()
        self._conn.close()
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            if self.q is False:
                self.commit()
            self.close()
        else:
            logger.error(f'EXCType: {exc_type}; EXCValue: {exc_val}; EXCTraceback: {exc_tb}')


class QbotDB(MysqlPool):
    """
    qbotdb连接池，lable: userinfo, corpus
    """
    def __init__(self,) -> None:
        super().__init__('qbotdb', pool_name='qbotdb', **dbcfg.dict())


class GalleryDB(MysqlPool):
    """
    美图图库连接池，lable: gallery
    """
    def __init__(self,) -> None:
        super().__init__('gallery', pool_name='gallery', **dbcfg.dict())


if __name__ == "__main__":
    # print(dbcfg.json())
    # print(dbcfg.dict())
    with QbotDB() as qb:
        result = qb.queryall('select * from corpus where ID>2000')
        # result = qb.queryone('select * from userinfo limit 2')
        print(result)
