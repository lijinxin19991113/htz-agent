"""
执行模块 - Windows 端鼠标键盘操作
"""
import time
import random
import win32gui
import win32api
import win32con
from typing import Tuple, Optional

from .config import Config


class Executor:
    """Windows 平台操作执行器"""

    def __init__(self):
        self.cfg = Config()
        self.delay = self.cfg.delay
        self.anti_ban = self.cfg.get("anti_ban", {})
        self.hwnd = None
        self._find_window()

    def _find_window(self):
        """查找游戏窗口（前缀匹配）"""
        import win32gui

        prefix = self.cfg.get("game.window_title_prefix", "")

        # 通过前缀枚举查找
        windows = []
        def enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and title.startswith(prefix):
                    ctx.append(hwnd)

        win32gui.EnumWindows(enum_handler, windows)

        if windows:
            self.hwnd = windows[0]
            title = win32gui.GetWindowText(self.hwnd)
            print(f"[执行器] 找到窗口: '{title}' (hwnd={self.hwnd})")
        else:
            raise RuntimeError(f"找不到游戏窗口，前缀: '{prefix}'")

        # 激活窗口
        win32gui.SetForegroundWindow(self.hwnd)
        time.sleep(0.1)

    def _random_delay(self, base: float = None):
        """随机延迟（防封）"""
        if base is None:
            base = self.delay.get("action", 0.3)
        min_d = self.delay.get("random_min", 0.1)
        max_d = self.delay.get("random_max", 0.5)
        t = base + random.uniform(min_d, max_d)
        time.sleep(t)

    def _get_client_coord(self, x: int, y: int) -> Tuple[int, int]:
        """屏幕坐标转客户端坐标"""
        if self.hwnd:
            left, top, _, _ = win32gui.GetWindowRect(self.hwnd)
            return left + x, top + y
        return x, y

    # ==================== 鼠标操作 ====================

    def click(self, x: int, y: int, button: str = "left"):
        """点击指定坐标"""
        sx, sy = self._get_client_coord(x, y)
        win32api.SetCursorPos((sx, sy))
        self._random_delay(0.05)

        if button == "left":
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
        else:
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0)

        self._random_delay()

    def double_click(self, x: int, y: int):
        """双击"""
        self.click(x, y)
        time.sleep(0.1)
        self.click(x, y)

    def right_click(self, x: int, y: int):
        """右键点击"""
        self.click(x, y, button="right")

    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
        """拖拽"""
        sx1, sy1 = self._get_client_coord(x1, y1)
        sx2, sy2 = self._get_client_coord(x2, y2)

        win32api.SetCursorPos((sx1, sy1))
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        time.sleep(0.05)

        # 模拟人类轨迹
        steps = int(duration / 0.01)
        for i in range(steps + 1):
            t = i / steps
            # 贝塞尔曲线插值（带微微抖动）
            cx = int(sx1 + (sx2 - sx1) * t + random.randint(-3, 3))
            cy = int(sy1 + (sy2 - sy1) * t + random.randint(-3, 3))
            win32api.SetCursorPos((cx, cy))
            time.sleep(0.01)

        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
        self._random_delay()

    # ==================== 键盘操作 ====================

    def key_press(self, key_code: int):
        """按下一个键"""
        win32api.keybd_event(key_code, 0, 0, 0)
        time.sleep(random.uniform(0.05, 0.1))
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)
        self._random_delay()

    def key_down(self, key_code: int):
        win32api.keybd_event(key_code, 0, 0, 0)

    def key_up(self, key_code: int):
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)

    def type_text(self, text: str):
        """输入文字（仅限英文）"""
        for char in text:
            if char.isupper():
                win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
                win32api.keybd_event(ord(char), 0, 0, 0)
                win32api.keybd_event(ord(char), 0, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
            elif char == " ":
                win32api.keybd_event(win32con.VK_SPACE, 0, 0, 0)
                win32api.keybd_event(win32con.VK_SPACE, 0, win32con.KEYEVENTF_KEYUP, 0)
            else:
                win32api.keybd_event(ord(char), 0, 0, 0)
                win32api.keybd_event(ord(char), 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(random.uniform(0.03, 0.08))
        self._random_delay()

    # ==================== 常用快捷键 ====================

    def press_esc(self):
        """ESC 键"""
        self.key_press(win32con.VK_ESCAPE)

    def press_enter(self):
        """回车键"""
        self.key_press(win32con.VK_RETURN)

    def press_f9(self):
        """F9"""
        self.key_press(0x78)  # F9

    # ==================== 窗口操作 ====================

    def activate_window(self):
        """激活游戏窗口"""
        if self.hwnd:
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.2)

    def get_window_rect(self) -> Tuple[int, int, int, int]:
        """获取窗口矩形 (left, top, right, bottom)"""
        if self.hwnd:
            return win32gui.GetWindowRect(self.hwnd)
        return (0, 0, 0, 0)

    # ==================== 组合动作 ====================

    def click_button(self, name: str, positions: dict):
        """根据按钮名点击（按钮位置由视觉识别提供）"""
        if name not in positions:
            return False
        x, y = positions[name]
        self.click(x, y)
        return True

    def move_to_and_click(self, target_x: int, target_y: int):
        """移动到目标并点击（带人类轨迹）"""
        cx, cy = win32api.GetCursorPos()
        self.drag(cx, cy, target_x, target_y, duration=random.uniform(0.3, 0.6))


# ==================== 常用键码 ====================
VK_CODES = {
    "esc": win32con.VK_ESCAPE,
    "enter": win32con.VK_RETURN,
    "space": win32con.VK_SPACE,
    "tab": win32con.VK_TAB,
    "shift": win32con.VK_SHIFT,
    "ctrl": win32con.VK_CONTROL,
    "alt": win32con.VK_MENU,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "a": ord("A"), "b": ord("B"), "c": ord("C"), "d": ord("D"),
    "e": ord("E"), "f": ord("F"), "g": ord("G"), "h": ord("H"),
    "i": ord("I"), "j": ord("J"), "k": ord("K"), "l": ord("L"),
    "m": ord("M"), "n": ord("N"), "o": ord("O"), "p": ord("P"),
    "q": ord("Q"), "r": ord("R"), "s": ord("S"), "t": ord("T"),
    "u": ord("U"), "v": ord("V"), "w": ord("W"), "x": ord("X"),
    "y": ord("Y"), "z": ord("Z"),
    "0": ord("0"), "1": ord("1"), "2": ord("2"), "3": ord("3"),
    "4": ord("4"), "5": ord("5"), "6": ord("6"), "7": ord("7"),
    "8": ord("8"), "9": ord("9"),
}


if __name__ == "__main__":
    # 测试（需要游戏窗口打开）
    try:
        exe = Executor()
        print(f"窗口句柄: {exe.hwnd}")
        print("Executor 初始化成功")
    except Exception as e:
        print(f"初始化失败: {e}")
