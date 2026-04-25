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
        self.temp_file = "/tmp/mhxy_screenshot.png"

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
            title = self.cfg.get("game.window_title")
            hwnd = win32gui.FindWindow(None, title)
            if not hwnd:
                raise RuntimeError(f"找不到窗口: {title}")

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            # 截取指定窗口区域
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
            path = f"/tmp/mhxy_{int(time.time())}.png"
        image.save(path)
        return path


if __name__ == "__main__":
    # 测试截图
    cap = ScreenCapture()
    img = cap.capture()
    print(f"截图尺寸: {img.size}")
    cap.save(img)
