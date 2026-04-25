"""
任务基类
"""
import time
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.screenshot import ScreenCapture
from core.vision import Vision, VisionResult, SceneType
from core.decision import DecisionMaker
from core.executor import Executor
from core.config import Config


logger = logging.getLogger("tasks")


class TaskStatus(Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class TaskResult:
    success: bool
    message: str
    rounds_completed: int = 0
    errors: int = 0


class BaseTask:
    """
    任务基类

    子类需要实现：
    - step(): 单轮任务执行
    - check_complete(): 检查任务是否完成
    """

    name: str = "base"

    def __init__(self, max_rounds: int = 20):
        self.cfg = Config()
        self.max_rounds = max_rounds
        self.round = 0
        self.errors = 0

        # 初始化核心组件
        self.cap = ScreenCapture()
        self.vision = Vision(use_cuda=True)
        self.decision = DecisionMaker()
        self.exe = Executor()

        # 截图间隔
        self.capture_interval = self.cfg.get("capture_interval", 0.5)

    def run(self) -> TaskResult:
        """主循环"""
        logger.info(f"[{self.name}] 任务开始，最多 {self.max_rounds} 轮")

        while self.round < self.max_rounds:
            self.round += 1
            logger.info(f"[{self.name}] 第 {self.round}/{self.max_rounds} 轮")

            try:
                # 截图
                img = self.cap.capture()

                # 视觉识别
                vr = self.vision.classify_scene(img)

                # 执行一步
                ok = self.step(img, vr)
                if not ok:
                    self.errors += 1
                    logger.warning(f"[{self.name}] 第 {self.round} 轮执行失败")

                # 检查是否完成
                if self.check_complete(vr):
                    logger.info(f"[{self.name}] 任务完成！")
                    return TaskResult(
                        success=True,
                        message=f"完成 {self.round} 轮",
                        rounds_completed=self.round,
                        errors=self.errors
                    )

            except Exception as e:
                self.errors += 1
                logger.error(f"[{self.name}] 第 {self.round} 轮异常: {e}")

            time.sleep(self.capture_interval)

        logger.info(f"[{self.name}] 达到最大轮数 {self.max_rounds}，退出")
        return TaskResult(
            success=False,
            message=f"达到最大轮数 {self.max_rounds}",
            rounds_completed=self.round,
            errors=self.errors
        )

    def step(self, img, vr: VisionResult) -> bool:
        """
        执行一步操作
        返回 True 表示继续，返回 False 表示异常
        """
        raise NotImplementedError

    def check_complete(self, vr: VisionResult) -> bool:
        """检查任务是否完成"""
        return self.round >= self.max_rounds

    def wait_for_scene(self, target_scene: SceneType, timeout: int = 30) -> bool:
        """等待进入目标场景"""
        start = time.time()
        while time.time() - start < timeout:
            img = self.cap.capture()
            vr = self.vision.classify_scene(img)
            if vr.scene == target_scene:
                return True
            time.sleep(1)
        return False

    def click_center(self, bbox) -> bool:
        """点击 BBox 中心"""
        if bbox is None:
            return False
        w, h = self.cap.capture().size
        cx, cy = bbox.to_xy_absolute(w, h)
        self.exe.click(cx, cy)
        return True
