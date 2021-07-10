from random import randint, choice
from typing import List, Optional, Dict
from src.common import logger
from src.common.levelsystem import UserLevel


class Player:
    """玩家

    Attributes:
        p (int):  所在罗盘的玩家索引 p1、p2
        id (int):  玩家id，通常是qq号
        bet (int):  玩家当前赌注
        left_times (int):  剩余道具可使用次数
        used_times (int):  已使用的道具数量
        items (Dict[str: int]):  玩家道具列表
        used_items (Dict[str: int]):  玩家使用过的道具，结算时扣取
        status (List[str]):  玩家buff、debuff
        medals (Dict[str:Union[bool, int]]):  勋章，根据战斗情况会获得
    """
    def __init__(self, p: int,  # 所在罗盘的玩家索引 p1、p2
                id: int,  # 玩家id，通常是qq号
                bet: int,  # 玩家当前赌注
                left_times: int,  # 剩余道具可使用次数
                used_times: int=0,  # 已使用的道具数量
                items: Dict={},  # 玩家道具列表
                used_items: Dict={},  # 玩家使用过的道具，结算时扣取
                status: List=[],  # 玩家buff、debuff
                medals: Dict={
                    'one_hit': False,  # 一发入魂，第一枪就中了
                    'counterattack': 0,  # 决死反击，不使用道具的话必中的回合没死就会触发，另外同归于尽的情况也算
                    'counterattack_win': False,  # 反击致胜，不使用道具的情况下必中的回合反而胜利
                    'super_duck': 0,  # 极限闪避， 对自己射击了等同于回合数的次数获得一个
                    'prop_expert ': False,  # 道具专家，使用了初始道具限制二倍数量的道具时获得
                    'take_it_easy': False  # 从容不迫，对方使用了三次道具以上而自己一次道具未使用就获胜
                    }  # 勋章，根据战斗情况会获得
                ) -> None:
        self.p, self.id, self.bet, self.left_times, self.used_times, self.items, self.used_items, self.status, self.medals\
        = p, id, bet, left_times, used_times, items, used_items, status, medals

    def use_item(self, item: str):
        """使用道具，有temp道具时会优先使用temp道具

        Args:
            item (str): 道具名字

        Returns:
            bool: 是否使用成功，如果剩余没有剩余次数则会返回false
        """
        assert item in self.items and self.items[item] > 0 or f'{item}_temp' in self.items and self.items[f'{item}_temp'] > 0, "该玩家没有这个道具"

        if self.left_times > 0:
            item = item if f'{item}_temp' not in self.items and self.items[f'{item}_temp'] > 0 else f'{item}_temp'  # 如果有相同的临时道具先用临时的
            self.items[item] -= 1
            self.used_items[item] += 1
            self.left_times -= 1
            self.used_items += 1
            return True
        else:
            return False

{
    'p': int,  # 所在罗盘的玩家索引 p1、p2
    'id': int,  # 玩家id，通常是qq号
    'bet': int,  # 玩家当前赌注
    'status': [],  # 玩家buff、debuff
    'left_times': int,  # 剩余道具可使用次数
    'used_tims': int,  # 已使用的道具数量
    'items': Dict[
                'item': int  # 该道具持有数量, 临时道具要在后面加上 _temp
                ],  # 玩家道具列表
    'used_items' :Dict[
                    'item': int  # 使用的数量
                ],  # 玩家使用过的道具，结算时扣取
    'medal': {
            'one_hit': bool,  # 一发入魂，第一枪就中了
            'counterattack': int,  # 决死反击，不使用道具的话必中的回合没死就会触发，另外同归于尽的情况也算
            'counterattack_win': bool,  # 反击致胜，不使用道具的情况下必中的回合反而胜利
            'super_duck': int,  # 极限闪避， 对自己射击了等同于回合数的次数获得一个
            'prop_expert ': bool,  # 道具专家，使用了初始道具限制二倍数量的道具时获得
            'take_it_easy': bool  # 从容不迫，对方使用了三次道具以上而自己一次道具未使用就获胜
            }  # 勋章，根据战斗情况会获得
}


class Roulette:
    def __init__(self, *players: Player,  # 玩家
                punishment: bool=False,  # 是否开启结算惩罚
                cru_round: int=1,  # 当前回合
                init_rounds : int=6,  # 初始总回合数
                rounds: Optional[int]=None,  # 当前总回合数
                init_danpos : Optional[int]=None,  # 子弹初始位置
                danpos: Optional[int]=None,  # 当前子弹所处位置
                cru_player: int=1,  # 当前玩家回合
                sheet: List=[],  # 行动表，记录玩家过去的出招顺序
                status: List=[]  # 罗盘状态列表
                ) -> None:
        self.players = {}
        for i, p in enumerate(players):
            self.players[i] = p
  
        self.init_danpos = init_danpos if init_danpos is not None else randint(1, rounds)
        self.danpos = danpos if danpos is not None else self.init_danpos
        
        self.init_rounds = init_rounds
        self.rounds = rounds if rounds is not None else self.init_rounds

        self.punishment, self.cru_round, self.cru_player, self.sheet, self.status = punishment, cru_round, cru_player, sheet, status
        def rlt():
            n = 0
            x = None
            while True:
                n += 1
                if x is not None:
                    n = x
                if n > self.rounds:
                    n = 1
                x = yield n

        self.rlt = rlt()  # 罗盘生成器，在1-rounds之间循环迭代
        self.crupos = next(self.rlt)  # 当前弹槽位置，启动轮盘，初始值为1

    def shoot(self):
        player = self.players[self.cru_player]
        logger.debug(f'player {self.cru_player} act in the current round: {self.cru_player}')
        if self.danpos == self.crupos:
            self.end()
            return True  # 对局结束
        else:
            return False