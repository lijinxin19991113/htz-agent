"""
导航模块
利用游戏内置自动寻路，实现地图间的移动
"""
import time
from typing import Optional, Tuple

from .executor import Executor
from .ocr import OCRReader
from .maps import MapDatabase
from .game_state import GameState


class Navigator:
    """
    导航器

    利用游戏内置自动寻路功能，通过以下步骤实现移动：
    1. 识别当前地图名称
    2. 在小地图上点击目标位置
    3. 等待移动完成
    """

    def __init__(self):
        self.exe = Executor()
        self.ocr = OCRReader()
        self.map_db = MapDatabase()
        self.game_state = GameState()
        self.last_map = ""

    def get_current_map(self, screenshot) -> str:
        """
        识别当前所在地图

        Args:
            screenshot: PIL Image

        Returns:
            str: 地图名称
        """
        map_name = self.ocr.read_map_name(screenshot)
        if map_name:
            self.game_state.update_map(map_name=map_name)
            self.last_map = map_name
        return map_name

    def navigate_to(self, target: str, timeout: float = 60.0) -> bool:
        """
        导航到目标（NPC 或地点）

        Args:
            target: 目标名称（如 "师傅"、"钟馗"）
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功到达
        """
        from .screenshot import ScreenCapture

        cap = ScreenCapture()
        cap.activate_window()

        # 识别当前地图
        img = cap.capture()
        current_map = self.get_current_map(img)

        print(f"[导航] 当前地图: {current_map}, 目标: {target}")

        # 查找目标位置
        # 优先在当前地图查找
        target_pos = self.map_db.get_npc_position(current_map, target)

        # 如果当前地图找不到，尝试在其他地图查找
        if target_pos is None:
            result = self.map_db.find_npc_in_map(target)
            if result:
                target_map, tx, ty = result
                print(f"[导航] 目标在 {target_map}，需要先移动到该地图")
                # TODO: 实现跨地图移动（需要传送或跑图）
                return False
            else:
                print(f"[导航] 未找到目标: {target}")
                return False

        # 在小地图上点击目标位置
        w, h = img.size
        target_x = int(target_pos[0] * w)
        target_y = int(target_pos[1] * h)

        print(f"[导航] 在小地图点击 ({target_x}, {target_y})")

        # 点击小地图触发自动寻路
        self.exe.click(target_x, target_y)

        # 等待移动完成
        return self._wait_for_arrival(target, timeout)

    def _wait_for_arrival(self, target: str, timeout: float) -> bool:
        """
        等待到达目标

        Args:
            target: 目标名称
            timeout: 超时时间

        Returns:
            bool: 是否成功到达
        """
        from .screenshot import ScreenCapture

        cap = ScreenCapture()
        start_time = time.time()
        check_interval = 2.0  # 每 2 秒检查一次

        print(f"[导航] 等待移动完成...")

        while time.time() - start_time < timeout:
            time.sleep(check_interval)

            img = cap.capture()
            current_map = self.get_current_map(img)

            # 检查是否到达目标地图/区域
            # TODO: 更精确的到达判断（比如识别 NPC 头像）
            if current_map != self.last_map:
                print(f"[导航] 地图已切换到: {current_map}")
                # 可以在这里进一步检查是否到达目标 NPC

            # 简短等待
            time.sleep(1)

        print(f"[导航] 等待超时")
        return False

    def click_on_minimap(self, x: float, y: float) -> bool:
        """
        直接在小地图上点击指定坐标

        Args:
            x: 归一化坐标 x (0-1)
            y: 归一化坐标 y (0-1)

        Returns:
            bool: 是否成功
        """
        from .screenshot import ScreenCapture

        cap = ScreenCapture()
        cap.activate_window()

        img = cap.capture()
        w, h = img.size

        click_x = int(x * w)
        click_y = int(y * h)

        print(f"[导航] 小地图点击 ({click_x}, {click_y})")
        self.exe.click(click_x, click_y)

        return True

    def navigate_to_coordinates(self, x: float, y: float, timeout: float = 30.0) -> bool:
        """
        导航到指定坐标

        Args:
            x: 归一化坐标 x (0-1)
            y: 归一化坐标 y (0-1)
            timeout: 超时时间

        Returns:
            bool: 是否成功到达
        """
        from .screenshot import ScreenCapture

        cap = ScreenCapture()
        cap.activate_window()

        print(f"[导航] 移动到坐标 ({x:.2f}, {y:.2f})")
        self.exe.click(int(x * 1000), int(y * 1000))

        time.sleep(timeout)
        return True


if __name__ == "__main__":
    # 测试
    nav = Navigator()

    # 测试识别当前地图
    from core.screenshot import ScreenCapture
    cap = ScreenCapture()
    cap.activate_window()
    img = cap.capture()

    current_map = nav.get_current_map(img)
    print(f"当前地图: {current_map}")

    # 测试查找 NPC
    result = nav.map_db.find_npc_in_map("师傅")
    if result:
        print(f"师傅位置: 地图={result[0]}, 坐标=({result[1]:.2f}, {result[2]:.2f})")
