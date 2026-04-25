"""
游戏状态管理
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum


class Sect(Enum):
    """门派枚举（幻唐志门派）"""
    UNKNOWN = "unknown"
    # 以下根据幻唐志实际门派填写
    WUSHEN = "武神"           # 测试用
    TIANSHU = "天师"
    FENGCHEN = "风辰"
    QINGLONG = "青龙"
    BAIHU = "白虎"
    ZHUQUE = "朱雀"
    XUANWU = "玄武"


class MapType(Enum):
    """地图类型"""
    UNKNOWN = "unknown"
    CITY = "city"          # 主城
    FIELD = "field"        # 野外
    DUNGEON = "dungeon"    # 副本
    BATTLE = "battle"      # 战斗中


@dataclass
class RoleInfo:
    """角色信息"""
    name: str = ""
    level: int = 0
    sect: Sect = Sect.UNKNOWN
    hp: int = 0
    max_hp: int = 0
    mp: int = 0
    max_mp: int = 0
    exp: int = 0
    gold: int = 0


@dataclass
class BattleUnit:
    """战斗单位"""
    name: str
    hp: int
    max_hp: int
    is_enemy: bool
    bbox: tuple = None  # (x1, y1, x2, y2) 归一化


@dataclass
class BattleState:
    """战斗状态"""
    in_battle: bool = False
    turn: int = 0
    my_units: List[BattleUnit] = field(default_factory=list)
    enemy_units: List[BattleUnit] = field(default_factory=list)
    is_auto: bool = False  # 是否自动战斗


@dataclass
class TaskProgress:
    """任务进度"""
    name: str = ""
    description: str = ""
    target: str = ""  # 目标 NPC 或坐标
    count: int = 0    # 当前计数
    total: int = 0    # 总数


class GameState:
    """
    游戏状态管理器

    全局单例，记录游戏运行时的各种状态
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化状态"""
        self.role = RoleInfo()
        self.battle = BattleState()
        self.current_map = ""
        self.map_type = MapType.UNKNOWN
        self.task = TaskProgress()
        self.last_update = 0

    def reset(self):
        """重置状态"""
        self._init()

    def update_role(self, **kwargs):
        """更新角色信息"""
        for k, v in kwargs.items():
            if hasattr(self.role, k):
                setattr(self.role, k, v)

    def update_battle(self, in_battle: bool = None, turn: int = None,
                     my_units: List[BattleUnit] = None,
                     enemy_units: List[BattleUnit] = None,
                     is_auto: bool = None):
        """更新战斗状态"""
        if in_battle is not None:
            self.battle.in_battle = in_battle
        if turn is not None:
            self.battle.turn = turn
        if my_units is not None:
            self.battle.my_units = my_units
        if enemy_units is not None:
            self.battle.enemy_units = enemy_units
        if is_auto is not None:
            self.battle.is_auto = is_auto

    def update_task(self, name: str = None, description: str = None,
                    target: str = None, count: int = None, total: int = None):
        """更新任务进度"""
        if name is not None:
            self.task.name = name
        if description is not None:
            self.task.description = description
        if target is not None:
            self.task.target = target
        if count is not None:
            self.task.count = count
        if total is not None:
            self.task.total = total

    def update_map(self, map_name: str = None, map_type: MapType = None):
        """更新地图信息"""
        if map_name is not None:
            self.current_map = map_name
        if map_type is not None:
            self.map_type = map_type

    def to_dict(self) -> dict:
        """转 dict（用于 API 决策）"""
        return {
            "role": {
                "name": self.role.name,
                "level": self.role.level,
                "sect": self.role.sect.value if self.role.sect else "unknown",
                "hp": self.role.hp,
                "max_hp": self.role.max_hp,
                "mp": self.role.mp,
                "max_mp": self.role.max_mp,
            },
            "battle": {
                "in_battle": self.battle.in_battle,
                "turn": self.battle.turn,
                "is_auto": self.battle.is_auto,
                "my_units_count": len(self.battle.my_units),
                "enemy_units_count": len(self.battle.enemy_units),
            },
            "map": {
                "name": self.current_map,
                "type": self.map_type.value,
            },
            "task": {
                "name": self.task.name,
                "description": self.task.description,
                "target": self.task.target,
                "count": self.task.count,
                "total": self.task.total,
            }
        }


# 全局单例
game_state = GameState()
