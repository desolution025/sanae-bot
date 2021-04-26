from pathlib import Path
import ujson as json
from datetime import datetime, timedelta
from typing import List, Union
try:
    from src.common import logger
except ImportError:
    from loguru import logger

# TODO: 防止好友拉入别的群，限制黑名单改为只响应白名单

block_groups_file = Path(__file__).parent/"block_groups.json"
block_users_file = Path(__file__).parent/"block_users.json"


# block_groups = {}  # 忽略群名单
# block_users = {}  # 忽略用户名单


if not block_groups_file.exists():
    with block_groups_file.open('w', encoding='utf-8') as j:
        json.dump({}, j, indent=4)

if not block_users_file.exists():
    with block_users_file.open('w', encoding='utf-8') as j:
        json.dump({}, j, indent=4)


# with block_groups_file.open(encoding='utf-8') as j:
#     block_groups = json.load(j)
# with block_users_file.open(encoding='utf-8') as j:
#     block_users = json.load(j)


class Blocker:
    '''
    控制群与用户的阻塞列表的基类
    群与用户阻塞规则reason:
    0: 通用规则，违规封禁，暂不加入解封方式(实际上暂时没有针对群的违规理由，只有针对个人)
    1：用户规则，用户主动加入阻塞名单，暂不加入解封方式
    2：用户规则，临时阻塞，6小时限制
    3: 群规则，由管理员使用off指令禁用，查询时仍然返回false，使用on指令主动解除
    '''
    block_list = {}  # 阻塞列表，群与用户的子类会使用不同的列表

    def __init__(self, id: int) -> None:
        self.id = str(id)
        self.file = Path()  # 文件，用于子类的记录文件

    def check_block(self) -> bool:
        '''
        检测是否为阻塞id
        '''
        block_ls = self.__class__.block_list
        # reason为2根据时间解禁，其他返回false，未禁止返回true
        if self.id in block_ls:
            if block_ls[self.id]['reason'] != 2:
                return False
            else:
                add_time = datetime.strptime(block_ls[id]['add_time'], "%Y-%m-%d %H:%M:%S")
                if datetime.now() - add_time < timedelta(hours=6):
                    return False
                else:
                    self.rm_block()
                    return True
        else:
            return True

    def add_block(self, reason: int):
        '''
        群与用户阻塞规则reason:
        0: 通用规则，违规封禁，暂不加入解封方式(实际上暂时没有针对群的违规理由，只有针对个人)
        1：用户规则，用户主动加入阻塞名单，暂不加入解封方式
        2：用户规则，临时阻塞，6小时限制
        3: 群规则，由管理员使用off指令禁用，查询时仍然返回false，使用on指令主动解除
        可能会根据原因加入解封规则
        '''
        add_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            'reason': reason,
            'add_time': add_time
        }
        self.__class__.block_list[self.id] = data
        with self.file.open('w', encoding='utf-8') as j:
            json.dump(self.__class__.block_list, j, indent=4)

    def rm_block(self):
        '''
        移出阻塞列表
        '''
        block_ls = self.__class__.block_list
        del block_ls[self.id]
        with self.file.open('w', encoding='utf-8') as j:
            json.dump(self.__class__.block_list, j, indent=4)

        
class Group_Blocker(Blocker):
    '''
    管理阻塞群组的类 ※gid会被转化为str，查询时要注意
    '''
    with block_groups_file.open(encoding='utf-8') as j:
        block_list = json.load(j)

    def __init__(self, gid: int) -> None:
        self.id = str(gid)
        self.file = block_groups_file

    def turn_on(self) -> bool:
        '''
        当reason为3时可调用此解禁方式，解禁同时返回true
        当reason不为3时不予解禁并且返回false
        '''
        if self.__class__.block_list[self.id]['reason'] == 3:
            self.rm_block()
            logger.info(f'Remove group {self.id} from block list')
            return True
        else:
            logger.info(f'Failed to unblock group {self.id} , reason: {self.__class__.block_list[self.id]["reason"]}')
            return False


class User_Blocker(Blocker):
    '''
    管理阻塞用户的类 ※uid会被转化为str，查询时要注意
    '''
    with block_users_file.open(encoding='utf-8') as j:
        block_list = json.load(j)

    def __init__(self, uid: int) -> None:
        self.id = str(uid)
        self.file = block_users_file


#——————白名单群组——————


enable_groups_file = Path(__file__).parent/"enable_groups.json"


if not enable_groups_file.exists():
    with enable_groups_file.open('w', encoding='utf-8') as j:
        json.dump({}, j, indent=4)


class Enable_Group:

    with enable_groups_file.open(encoding='utf-8') as j:
        enable_groups : dict = json.load(j)

    def __init__(self, gid: Union[int, str]) -> None:
        self.gid = str(gid)

    def check_enable(self):
        # TODO: 检查到期时间
        if self.gid in self.__class__.enable_groups:
            return True
        else:
            return False
        
    def approve(self, term: int):
        if self.gid in self.__class__.enable_groups:
            return False
        else:
            data = {
                'authorize_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'lease_term': term
            }
            self.__class__.enable_groups[self.gid] = data
            with enable_groups_file.open('w', encoding='utf-8') as j:
                json.dump(self.__class__.enable_groups, j, indent=4)
            return True

    def renewal(self, term: int):
        if self.gid not in self.__class__.enable_groups:
            self.approve(term)
        else:
            self.__class__.enable_groups[self.gid]['lease_term'] += term
            with enable_groups_file.open('w', encoding='utf-8') as j:
                json.dump(self.__class__.enable_groups, j, indent=4)



if __name__ == "__main__":
    blocker1 = User_Blocker(112)
    blocker1.rm_block()
    print(blocker1.check_block())