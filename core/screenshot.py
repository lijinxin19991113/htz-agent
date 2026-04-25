"""
截图模块 - 支持 ADB（安卓模拟器）和 Windows 窗口截图
"""
import subprocess
import time
from pathlib import Path
from PIL import Image
import io

from .config import Config


class ScreenCapture:
    """截图管理类"""

    def __init__(self):
        self.cfg = Config()
        self.platform = self.cfg.get("game.platform")
        self.adb_serial = self.cfg.get("game.adb_serial")
        self.temp_file = "/tmp/htz_screenshot.png"
        self._hwnd = None

    # ==================== ADB 截图 ====================

    def adb_screenshot(self) -> Image.Image:
        """通过 ADB 截图（安卓模拟器）"""
        try:
            subprocess.run(
                ["adb", "-s", self.adb_serial, "exec-out", "screencap", "-p"],
                stdout=open(self.temp_file, "wb"),
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            return Image.open(self.temp_file)
        except Exception as e:
            raise RuntimeError(f"ADB 截图失败: {e}")

    def adb_push(self, local_path: str, remote_path: str = "/sdcard/screenshot.png"):
        """推送文件到模拟器"""
        subprocess.run(
            ["adb", "-s", self.adb_serial, "push", local_path, remote_path],
            stderr=subprocess.DEVNULL,
            timeout=10,
        )

    def adb_pull(self, remote_path: str = "/sdcard/screenshot.png", local_path: str = None):
        """从模拟器拉取文件"""
        if local_path is None:
            local_path = self.temp_file
        subprocess.run(
            ["adb", "-s", self.adb_serial, "pull", remote_path, local_path],
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return local_path

    # ==================== Windows 截图 ====================

    def _find_window_by_prefix(self, prefix: str):
        """通过前缀查找窗口句柄"""
        import win32gui

        def enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and title.startswith(prefix):
                    ctx.append(hwnd)

        windows = []
        win32gui.EnumWindows(enum_handler, windows)
        return windows[0] if windows else None

    def _get_hwnd(self):
        """获取窗口句柄（带缓存）"""
        if self._hwnd is not None:
            return self._hwnd

        import win32gui

        prefix = self.cfg.get("game.window_title_prefix", "")

        # 优先尝试精确前缀匹配
        if prefix:
            hwnd = self._find_window_by_prefix(prefix)
            if hwnd:
                self._hwnd = hwnd
                import win32gui
                title = win32gui.GetWindowText(hwnd)
                print(f"[截图] 找到窗口: '{title}' (hwnd={hwnd})")
                return hwnd

        # 回退：尝试直接用 window_title_prefix 当完整标题
        hwnd = win32gui.FindWindow(None, prefix)
        if hwnd:
            self._hwnd = hwnd
            return hwnd

        raise RuntimeError(f"找不到窗口，前缀: '{prefix}'")

    def win_screenshot(self, hwnd=None) -> Image.Image:
        """Windows 窗口截图"""
        try:
            import win32gui
            import win32ui
            import win32con
            import mss
        except ImportError:
            raise RuntimeError("Windows 截图需要 pywin32 和 mss 库")

        if hwnd is None:
            hwnd = self._get_hwnd()

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        with mss.mss() as sct:
            monitor = {
                "left": left,
                "top": top,
                "width": width,
                "height": height,
            }
            img = sct.grab(monitor)
            return Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")

    # ==================== 统一接口 ====================

    def capture(self) -> Image.Image:
        """统一截图接口，根据配置自动选择方式"""
        if self.platform == "android":
            return self.adb_screenshot()
        elif self.platform == "windows":
            return self.win_screenshot()
        else:
            raise ValueError(f"不支持的平台: {self.platform}")

    def save(self, image: Image.Image, path: str = None) -> str:
        """保存截图到文件"""
        if path is None:
            path = f"/tmp/htz_{int(time.time())}.png"
        image.save(path)
        return path

    def activate_window(self):
        """激活游戏窗口"""
        import win32gui
        hwnd = self._get_hwnd()
        if hwnd:
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.2)


if __name__ == "__main__":
    cap = ScreenCapture()
    try:
        img = cap.capture()
        print(f"截图尺寸: {img.size}")
        cap.save(img)
        print("截图成功")
    except RuntimeError as e:
        print(f"截图失败: {e}")
