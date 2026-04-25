"""
视觉识别模块 - YOLOv8 检测 + 场景分类
支持任意分辨率输入，输出归一化坐标
"""
import cv2
import numpy as np
from PIL import Image
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from .config import Config


class SceneType(Enum):
    """场景类型枚举"""
    UNKNOWN = "unknown"
    IDLE = "idle"                    # 空闲/跑路
    BATTLE = "battle"                # 战斗
    BATTLE_MENU = "battle_menu"      # 战斗菜单
    DIALOG = "dialog"                # NPC 对话
    MENU = "menu"                    # 游戏菜单
    SHOP = "shop"                    # 商店
    MAP = "map"                      # 地图
    TASK_TRACK = "task_track"        # 任务追踪
    LOADING = "loading"              # 加载中
    ERROR = "error"                  # 异常/断线


@dataclass
class BBox:
    """检测框"""
    class_name: str
    confidence: float
    x1: float  # 归一化 0-1
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    def to_absolute(self, screen_w: int, screen_h: int) -> Tuple[int, int, int, int]:
        """归一化坐标转绝对像素坐标"""
        return (
            int(self.x1 * screen_w),
            int(self.y1 * screen_h),
            int(self.x2 * screen_w),
            int(self.y2 * screen_h),
        )

    def to_xy_absolute(self, screen_w: int, screen_h: int) -> Tuple[int, int]:
        """归一化坐标转绝对像素中心点"""
        cx = int((self.x1 + self.x2) / 2 * screen_w)
        cy = int((self.y1 + self.y2) / 2 * screen_h)
        return cx, cy


@dataclass
class BattleInfo:
    """战斗状态信息"""
    in_battle: bool = False
    turn: int = 0
    my_hp: int = 0
    my_max_hp: int = 0
    my_mp: int = 0
    my_max_mp: int = 0
    enemies: List[Dict] = field(default_factory=list)  # [{"name": "山贼", "hp": 500, "max_hp": 1000, "bbox": BBox}]
    allies: List[Dict] = field(default_factory=list)


@dataclass
class VisionResult:
    """视觉识别结果"""
    scene: SceneType
    confidence: float
    detections: List[BBox] = field(default_factory=list)  # 所有检测到的物体
    battle_info: Optional[BattleInfo] = None
    screen_size: Tuple[int, int] = (0, 0)


class YOLOv8Detector:
    """
    YOLOv8 检测器接口

    使用方式：
        detector = YOLOv8Detector(model_path="weights/htz.pt")
        results = detector.detect(image)  # image 是 numpy array 或 PIL Image
        # results = [BBox(...), BBox(...), ...]
    """

    def __init__(self, model_path: str = None, device: str = "cuda"):
        """
        初始化 YOLOv8 检测器

        Args:
            model_path: 模型权重路径，默认使用 assets/weights/htz.pt
            device: 运行设备，"cuda" 或 "cpu"
        """
        self.model = None
        self.model_path = model_path
        self.device = device
        self._loaded = False

    def _ensure_loaded(self):
        """延迟加载模型"""
        if self._loaded:
            return

        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError("请安装 ultralytics: pip install ultralytics")

        if self.model_path is None:
            # 默认路径
            import os
            base = os.path.dirname(os.path.dirname(__file__))
            self.model_path = os.path.join(base, "assets", "weights", "htz.pt")

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"YOLOv8 模型未找到: {self.model_path}")

        self.model = YOLO(self.model_path)
        if self.device == "cuda":
            self.model.to("cuda")
        self._loaded = True

    def detect(self, image) -> List[BBox]:
        """
        检测图像中的物体

        Args:
            image: numpy array (BGR) 或 PIL Image

        Returns:
            List[BBox]: 检测结果列表
        """
        self._ensure_loaded()

        # 确保是 numpy array BGR 格式
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        results = self.model.predict(image, verbose=False, conf=0.5)

        bboxes = []
        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue
            for box in boxes:
                # 归一化坐标 (0-1)
                x1, y1, x2, y2 = box.xyxyn[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                cls_name = self.model.names[cls_id]

                bboxes.append(BBox(
                    class_name=cls_name,
                    confidence=conf,
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                ))

        return bboxes


class Vision:
    """
    视觉识别主类

    支持两种模式：
    1. YOLOv8 模式（推荐）：使用训练好的 YOLOv8 模型检测
    2. Fallback 模式：模板匹配 + 颜色检测（无模型时使用）
    """

    # 按钮相对坐标（归一化 0-1，基于虚拟分辨率 960x540）
    # 这些是 YOLOv8 未训练前的保底位置
    BUTTON_POS = {
        "attack": (0.85, 0.75),
        "skill_1": (0.75, 0.80),
        "skill_2": (0.80, 0.80),
        "skill_3": (0.85, 0.80),
        "item": (0.70, 0.75),
        "defend": (0.65, 0.75),
        "auto": (0.90, 0.55),
        "confirm": (0.50, 0.70),
        "cancel": (0.40, 0.70),
        "close": (0.90, 0.10),
        "menu": (0.10, 0.85),
        "map": (0.90, 0.20),
        "task": (0.85, 0.40),
    }

    # YOLOv8 模型定义的类别（训练时定义）
    # 请根据实际训练时的 classes.txt 填写
    CLASSES = [
        "attack_btn",    # 攻击按钮
        "skill_btn",     # 技能按钮
        "item_btn",      # 道具按钮
        "defend_btn",    # 防御按钮
        "confirm_btn",   # 确认按钮
        "cancel_btn",    # 取消按钮
        "auto_btn",      # 自动战斗
        "hp_bar",        # 血条
        "mp_bar",        # 蓝条
        "enemy",         # 敌方单位
        "ally",          # 我方单位
        "npc",           # NPC
        "dialog",        # 对话框
        "menu",          # 菜单
        "shop",          # 商店
        "map",           # 小地图
        "monster",       # 怪物
    ]

    def __init__(self, yolo_model_path: str = None, use_cuda: bool = True):
        """
        初始化视觉识别模块

        Args:
            yolo_model_path: YOLOv8 模型路径
            use_cuda: 是否使用 GPU
        """
        self.cfg = Config()
        self.resolution = self.cfg.resolution

        # 优先尝试 YOLOv8 模式
        self.use_yolo = False
        self.detector = None

        try:
            self.detector = YOLOv8Detector(
                model_path=yolo_model_path,
                device="cuda" if use_cuda else "cpu"
            )
            # 测试模型是否可用
            self.detector._ensure_loaded()
            self.use_yolo = True
        except Exception as e:
            import warnings
            warnings.warn(f"YOLOv8 模型加载失败，使用 Fallback 模式: {e}")
            self.use_yolo = False

    def detect(self, image) -> List[BBox]:
        """
        检测图像中的物体

        Args:
            image: PIL Image 或 numpy array

        Returns:
            List[BBox]: 检测结果
        """
        if self.use_yolo:
            return self.detector.detect(image)
        else:
            # Fallback: 返回空（后续由场景分类器补充）
            return []

    def classify_scene(self, image) -> VisionResult:
        """
        场景分类主入口

        Args:
            image: PIL Image 或 numpy array

        Returns:
            VisionResult: 包含场景类型、检测结果、战斗信息
        """
        # 确保是 numpy array
        if isinstance(image, Image.Image):
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        else:
            img = image

        h, w = img.shape[:2]
        result = VisionResult(
            scene=SceneType.UNKNOWN,
            confidence=0.0,
            detections=[],
            screen_size=(w, h)
        )

        # 1. YOLOv8 检测（如果可用）
        if self.use_yolo:
            result.detections = self.detector.detect(image)

            # 根据检测结果判断场景
            class_counts = {}
            for det in result.detections:
                cls = det.class_name
                class_counts[cls] = class_counts.get(cls, 0) + 1

            # 场景判断逻辑
            if class_counts.get("hp_bar", 0) >= 2 and class_counts.get("enemy", 0) >= 1:
                result.scene = SceneType.BATTLE
                result.confidence = 0.95
            elif class_counts.get("dialog", 0) >= 1:
                result.scene = SceneType.DIALOG
                result.confidence = 0.90
            elif class_counts.get("menu", 0) >= 1:
                result.scene = SceneType.MENU
                result.confidence = 0.85
            elif class_counts.get("shop", 0) >= 1:
                result.scene = SceneType.SHOP
                result.confidence = 0.85
            elif class_counts.get("map", 0) >= 1:
                result.scene = SceneType.MAP
                result.confidence = 0.80
            else:
                result.scene = SceneType.IDLE
                result.confidence = 0.6

            # 提取战斗信息
            result.battle_info = self._extract_battle_info(result.detections)

        else:
            # Fallback: 使用传统方法
            result = self._fallback_classify(img)

        return result

    def _extract_battle_info(self, detections: List[BBox]) -> BattleInfo:
        """从检测结果中提取战斗信息"""
        info = BattleInfo()

        enemies = [d for d in detections if d.class_name == "enemy"]
        allies = [d for d in detections if d.class_name == "ally"]
        hp_bars = [d for d in detections if d.class_name == "hp_bar"]
        mp_bars = [d for d in detections if d.class_name == "mp_bar"]

        if enemies or hp_bars:
            info.in_battle = True
            info.enemies = [
                {"name": f"enemy_{i}", "hp": 0, "max_hp": 1000, "bbox": e}
                for i, e in enumerate(enemies)
            ]
            info.allies = [
                {"name": f"ally_{i}", "hp": 0, "max_hp": 1000, "bbox": a}
                for i, a in enumerate(allies)
            ]

        return info

    def _fallback_classify(self, img: np.ndarray) -> VisionResult:
        """Fallback 场景分类（无 YOLOv8 时使用）"""
        h, w = img.shape[:2]
        result = VisionResult(
            scene=SceneType.UNKNOWN,
            confidence=0.3,
            detections=[],
            screen_size=(w, h)
        )

        # 简化判断：检测颜色特征
        # 红色血条
        lower_red = np.array([0, 100, 100])
        upper_red = np.array([10, 255, 255])
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask_red = cv2.inRange(hsv, lower_red, upper_red)

        # 蓝色蓝量
        lower_blue = np.array([100, 150, 100])
        upper_blue = np.array([130, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

        red_ratio = np.sum(mask_red > 0) / (h * w)
        blue_ratio = np.sum(mask_blue > 0) / (h * w)

        if red_ratio > 0.01 and blue_ratio > 0.005:
            result.scene = SceneType.BATTLE
            result.confidence = 0.7
        else:
            result.scene = SceneType.IDLE
            result.confidence = 0.5

        return result

    # ==================== 工具方法 ====================

    def find_by_class(self, detections: List[BBox], class_name: str) -> List[BBox]:
        """查找指定类别的检测结果"""
        return [d for d in detections if d.class_name == class_name]

    def find_one(self, detections: List[BBox], class_name: str) -> Optional[BBox]:
        """查找第一个指定类别的检测结果"""
        results = self.find_by_class(detections, class_name)
        return results[0] if results else None

    def screen_to_absolute(self, rel_x: float, rel_y: float, screen_w: int, screen_h: int) -> Tuple[int, int]:
        """相对坐标转绝对坐标"""
        return int(rel_x * screen_w), int(rel_y * screen_h)

    def find_button(self, detections: List[BBox], button_name: str, screen_w: int, screen_h: int) -> Optional[Tuple[int, int]]:
        """
        查找按钮位置
        优先从 YOLOv8 检测结果中找，否则用保底坐标
        """
        # 先尝试从检测结果找
        btn = self.find_one(detections, button_name)
        if btn:
            return btn.to_xy_absolute(screen_w, screen_h)

        # Fallback 到保底坐标
        if button_name in self.BUTTON_POS:
            return self.screen_to_absolute(
                self.BUTTON_POS[button_name][0],
                self.BUTTON_POS[button_name][1],
                screen_w, screen_h
            )
        return None


if __name__ == "__main__":
    # 测试
    vision = Vision(use_cuda=True)
    print(f"YOLOv8 模式: {vision.use_yolo}")
    print(f"支持的类别: {vision.CLASSES}")
    print(f"保底按钮位置: {list(vision.BUTTON_POS.keys())}")
