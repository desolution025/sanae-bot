from random import random, randint, choice, choices
from datetime import datetime
from typing import Tuple, Optional

from src.common.levelsystem import UserLevel


CARD_LIST = []  # 符卡列表
ITEM_LIST = []  # 物品列表

miner = {
    'uid': {
        'time': datetime,  # 最后一次入场时间
        'cooling': int,  # 最后一次入场时开始的冷却时间，以分钟为单位
        'status': []  # 状态列表
    }
}

record = {
    'uid': int,  # 用户id
    'time': datetime,  # 入场时间
    'toll': int,  # 交付的费用
    'items': [],  # 使用的符卡
    'income': int,  # 获得的收入（金币）
    'reward': [str],  # 获得的奖励（道具之类）
}

distributions = {
    'name': float  # 道具名称及产出概率
}


Mines_Collection = {}  # 所有当前可以开采的矿洞


class Mine:
    def __init__(self, owner: int,  # 矿场主
                location: int, # 开矿地点，用于交互报告时通知矿场主的位置，群号，私聊开矿的则为0
                start_up_capital: int, # 启动资金
                stability: int,  # 结构稳定性
                breadth: int,  # 空间宽广度，代表单次符卡使用次数限制
                oof_prob: int,  # 金矿出产率，钱
                card_prob: int,  # 卡片出产率，符卡
                item_prob: int  # 物品出产率，卡片之类的
                ) -> None:
        self.owner, self.location, self.start_up_capital, self.stability, self.breadth, self.oof_prob, self.card_prob, self.item_prob\
            = owner, location, start_up_capital, stability, breadth, oof_prob, card_prob, item_prob
        self.fee = 10  # 当前入场费
        self.depth = 0  # 当前深度
        self.coll_prob = 0.005  # 当前坍塌率，随着深度加高
        self.income = 0  # 当前获得的收入
        self.distributions = {}  # 矿产分布，这个矿洞能产出的道具以及比率，比率应该会随着深度而成连续噪波变化
        self.status = []  # 状态，如加固、脆弱、矿产率上升下降之类的
        self.miners = {}  # 玩家列表，记录玩家冷却
        self.sheet = []  # 行动表，记录每次挖矿的玩家及其使用的符卡与获得的道具等信息

        while True:
            self.number = randint(1, 1000)
            if self.number not in Mines_Collection:
                Mines_Collection[self.number] = self
                break

    def coll_prob_up(self):
        """坍塌率上升  TODO:设计坍塌率上升算法"""
        self.coll_prob += 0.01

    def get_oof(self, *cards):
        """产出金币

        产出的概率与数额应该随depth加大而加大
        TODO: 设计概率与数额算法
        """
        if self.oof_prob * self.depth > random():
            return self.depth * self.fee
        else:
            return None

    def get_card(self, *cards):
        """产出符卡

        对可能产出的每个符卡进行概率计算，概率与depth和矿洞的符卡产出率应成正相关
        TODO: 设计符卡产出概率
        """
        rewards = []
        for name in [card for card in self.distributions if card in CARD_LIST]:
            if self.distributions['name'] * self.card_prob * self.depth > random():
                rewards.append(name)
        return rewards
            
    def get_item(self, *cards: str):
        """产出道具
        
        计算方式与符卡类似，TODO: 考虑是否要分开计算，还是合并计算
        """
        itemls = [item for item in self.distributions if item in ITEM_LIST]  # 物体列表
        probls = [self.distributions[p] for p in itemls]  # 概率列表
        if 'must' in cards:  # 必得道具得符
            return choices(itemls, probls)
        else:
            rewards = []
            for i, item in  enumerate(itemls):
                if probls[i] * self.card_prob * self.depth > random():
                    rewards.append(item)
            return rewards

    def get_rewards(self, cru_op, *cards):
        """获得道具，在挖矿成功时调用

        Args:
            cru_op (Dict): 当前的挖矿记录，获得的道具将向这个字典中添加
        """
        # 获得道具
        r_oof = self.get_oof(*cards)
        r_card = self.get_card(*cards)
        r_item = self.get_item(*cards)

        # 更新当前挖矿记录
        cru_op['income'] = r_oof
        cru_op['reward'] = r_card.extend(r_item)

        return r_oof, r_card, r_item

    def mine(self, uid: int, *cards: str):
        """执行开采

        Args:
            uid (int): 开采者ID

        Returns:
            Tuple[Bool, Optional[Tuple]]: 返回是否坍塌以及开采者获得的奖励，True为未坍塌，可继续开采
        """
        
        toll = self.fee  # 收取的费用
        if toll:
            self.income += self.fee
            UserLevel(uid).turnover(-toll)
        
        # 增加一条新的挖矿记录
        self.sheet.append(
                {
                    'uid': uid,  # 用户id
                    'time': datetime.now(),  # 入场时间
                    'toll': toll,  # 交付的费用
                    'items': cards,  # 使用的符卡
                    'income': 0,  # 获得的收入（金币）
                    'reward': [],  # 获得的奖励（道具之类）
                }
            )
        cru_op = self.sheet[-1]  # 添加步骤之后立刻获得当前步骤的引用

        if self.coll_prob < random():
            self.depth += 1  # 
            self.coll_prob_up()

            # 添加玩家最后进入时间，更新玩家状态
            self.miners[uid] = {
                'time': datetime.now(),  # 最后一次入场时间
                'cooling': 60,  # 最后一次入场时开始的冷却时间，以分钟为单位
                }
            if 'status' not in self.miners[uid]:
                self.miners[uid]['status'] = []
            else:
                self.miners[uid]['status'].append()
            
            # 计算奖励
            r_oof, r_card, r_item = self.get_rewards(cru_op, *cards)
    
            return True, (r_oof, r_card, r_item)

        else:  # 触发坍塌
            if 'escape' in cards:  # 逃脱符依然能获得奖励
                r_oof, r_card, r_item = self.get_rewards(cru_op, *cards)
                return False, (r_oof, r_card, r_item)
            self.collapse()
            return False, None

    def collapse(self):
        self.status.append('collapse')
        del Mines_Collection[self.number]


def all_mines():
    """返回当前正在开采的所有矿场"""
    return Mines_Collection


def mining_count(uid: int) -> int:
    """查询用户当前正在开发的矿场数量"""
    count = 0
    for i, mine in Mines_Collection.items():
        if mine.owner == uid:
            count += 1
    return count

def upper_limit(level: int) -> int:
    """当前等级可以同时开启的矿场上限

    暂定为从3级开始每两级可以开一个
    """
    if not level:
        return 0
    return (level - 1) // 2