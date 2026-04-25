"""
地图数据库模块
定义游戏中各地图的 NPC 位置和传送点信息
"""
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass
class MapLocation:
    """地图上的位置点"""
    name: str           # 位置名称（如 NPC 名称）
    x: float           # 归一化坐标 x (0-1)
    y: float           # 归一化坐标 y (0-1)
    description: str = ""  # 描述


@dataclass
class MapData:
    """地图数据"""
    name: str                          # 地图显示名
    map_type: str = "field"            # 地图类型: city, field, dungeon
    min_x: float = 0.0                 # 地图坐标范围
    max_x: float = 1000.0
    min_y: float = 0.0
    max_y: float = 1000.0
    npcs: Dict[str, MapLocation] = None  # NPC 位置
    portals: Dict[str, Tuple[str, float, float]] = None  # 传送点: 目标地图名 -> (目标地图, x, y)

    def __post_init__(self):
        if self.npcs is None:
            self.npcs = {}
        if self.portals is None:
            self.portals = {}


# 地图数据库
# 注意：这些坐标需要根据实际游戏进行调整
# 坐标是小地图上的点击位置，归一化到 0-1 范围

MAP_DATABASE: Dict[str, MapData] = {
    # === 主城 ===
    "长安城": MapData(
        name="长安城",
        map_type="city",
        min_x=0, max_x=1000,
        min_y=0, max_y=1000,
        npcs={
            # 师傅位置（师门任务用）
            "师傅": MapLocation("师傅", 0.5, 0.4, "师门任务 NPC"),
            # 其他常用 NPC
            "钟馗": MapLocation("钟馗", 0.6, 0.35, "抓鬼任务 NPC"),
            "镖头": MapLocation("镖头", 0.4, 0.5, "运镖任务 NPC"),
        },
        portals={}
    ),

    "清河镇": MapData(
        name="清河镇",
        map_type="city",
        npcs={
            "仓库管理员": MapLocation("仓库管理员", 0.5, 0.5, "存储物品"),
        }
    ),

    # === 野外地图 ===
    "清河镇野外": MapData(
        name="清河镇野外",
        map_type="field",
        npcs={}
    ),

    "长安城郊外": MapData(
        name="长安城郊外",
        map_type="field",
        npcs={}
    ),

    # === 地府 ===
    "地府": MapData(
        name="地府",
        map_type="dungeon",
        npcs={}
    ),

    # === 师门相关 ===
    "大唐官庄": MapData(
        name="大唐官庄",
        map_type="city",
        npcs={
            "师傅": MapLocation("师傅", 0.5, 0.4, "师门任务发布人"),
        }
    ),

    "天师府": MapData(
        name="天师府",
        map_type="city",
        npcs={
            "师傅": MapLocation("师傅", 0.5, 0.4, "师门任务发布人"),
        }
    ),

    "风辰殿": MapData(
        name="风辰殿",
        map_type="city",
        npcs={
            "师傅": MapLocation("师傅", 0.5, 0.4, "师门任务发布人"),
        }
    ),
}


class MapDatabase:
    """地图数据库访问类"""

    def __init__(self):
        self.maps = MAP_DATABASE

    def get_map(self, map_name: str) -> Optional[MapData]:
        """获取地图数据"""
        return self.maps.get(map_name)

    def get_npc_position(self, map_name: str, npc_name: str) -> Optional[Tuple[float, float]]:
        """
        获取 NPC 在小地图上的位置

        Args:
            map_name: 地图名称
            npc_name: NPC 名称

        Returns:
            Tuple[x, y]: 归一化坐标，如果未找到返回 None
        """
        map_data = self.get_map(map_name)
        if map_data and npc_name in map_data.npcs:
            npc = map_data.npcs[npc_name]
            return (npc.x, npc.y)
        return None

    def find_npc_in_map(self, npc_name: str) -> Optional[Tuple[str, float, float]]:
        """
        在所有地图中查找 NPC

        Args:
            npc_name: NPC 名称

        Returns:
            Tuple[地图名, x, y]: 如果找到返回地图名和坐标
        """
        for map_name, map_data in self.maps.items():
            if npc_name in map_data.npcs:
                npc = map_data.npcs[npc_name]
                return (map_name, npc.x, npc.y)
        return None

    def add_map(self, map_data: MapData):
        """添加新地图"""
        self.maps[map_data.name] = map_data

    def add_npc(self, map_name: str, npc_name: str, x: float, y: float, description: str = ""):
        """添加 NPC 到地图"""
        if map_name not in self.maps:
            self.maps[map_name] = MapData(name=map_name)

        self.maps[map_name].npcs[npc_name] = MapLocation(
            name=npc_name,
            x=x, y=y,
            description=description
        )


if __name__ == "__main__":
    db = MapDatabase()

    # 测试查找 NPC
    result = db.find_npc_in_map("师傅")
    if result:
        print(f"找到师傅: 地图={result[0]}, 位置=({result[1]:.2f}, {result[2]:.2f})")
    else:
        print("未找到师傅")
