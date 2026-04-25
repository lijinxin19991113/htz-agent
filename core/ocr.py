"""
OCR 文字识别模块
基于 EasyOCR，专注于游戏界面文字识别
"""
import os
import time
from typing import Optional, List, Tuple
from PIL import Image
import numpy as np
import cv2


class OCRReader:
    """OCR 文字识别器"""

    # 地图名称模板目录
    MAP_TEMPLATE_DIR = "assets/map_names"

    def __init__(self, languages: List[str] = None):
        """
        初始化 OCR 识别器

        Args:
            languages: 语言列表，默认 ['ch_sim', 'en']（简体中文 + 英文）
        """
        if languages is None:
            languages = ['ch_sim', 'en']

        self._reader = None
        self._languages = languages
        self._initialized = False
        self._map_templates = {}  # 缓存地图模板

    def _ensure_init(self):
        """延迟初始化 EasyOCR Reader"""
        if self._initialized:
            return

        import easyocr
        print("[OCR] 初始化 EasyOCR...")
        self._reader = easyocr.Reader(self._languages, verbose=False)
        self._initialized = True
        print("[OCR] 初始化完成")

    def _ensure_init(self):
        """延迟初始化 EasyOCR Reader"""
        if self._initialized:
            return

        import easyocr
        print("[OCR] 初始化 EasyOCR...")
        self._reader = easyocr.Reader(self._languages, verbose=False)
        self._initialized = True
        print("[OCR] 初始化完成")

    def read_text(self, image: Image.Image, region: Tuple[int, int, int, int] = None) -> List[str]:
        """
        读取图片中的文字

        Args:
            image: PIL Image
            region: 可选，指定区域 (x1, y1, x2, y2) 绝对像素坐标
                    如果为 None，则识别整张图片

        Returns:
            List[str]: 识别出的文字列表
        """
        self._ensure_init()

        # 转换图片格式
        if isinstance(image, Image.Image):
            img = np.array(image.convert('RGB'))
        else:
            img = image

        # 裁剪区域
        if region:
            x1, y1, x2, y2 = region
            img = img[y1:y2, x1:x2]

        # OCR 识别
        results = self._reader.readtext(img)

        # 提取文字
        texts = []
        for (bbox, text, confidence) in results:
            if confidence > 0.3:  # 过滤低置信度结果
                texts.append(text.strip())

        return texts

    def read_map_name(self, image: Image.Image) -> str:
        """
        读取地图名称

        优先使用模板匹配识别地图名，如果失败再用 OCR

        Args:
            image: PIL Image

        Returns:
            str: 地图名称，如果未识别到返回空字符串
        """
        # 1. 先尝试模板匹配
        map_name = self._match_map_template(image)
        if map_name:
            return map_name

        # 2. 如果没有加载模板或匹配失败，尝试 OCR 识别固定区域
        w, h = image.size

        # 地图名称区域（左上角小地图附近）
        region = (
            int(w * 0.02),
            int(h * 0.02),
            int(w * 0.15),
            int(h * 0.10)
        )

        texts = self.read_text(image, region=region)

        if not texts:
            return ""

        # 返回第一个非空结果（地图名称通常是最突出的文字）
        for text in texts:
            if len(text) >= 2:  # 地图名至少2个字符
                return text

        return texts[0] if texts else ""

    def _match_map_template(self, image: Image.Image) -> Optional[str]:
        """
        使用模板匹配识别地图名称

        Args:
            image: PIL Image

        Returns:
            str: 地图名称，如果未匹配到返回 None
        """
        # 加载模板（如果尚未加载）
        if not self._map_templates:
            self._load_map_templates()

        if not self._map_templates:
            return None

        # 转换图片
        if isinstance(image, Image.Image):
            img_cv = cv2.cvtColor(np.array(image.convert('RGB')), cv2.COLOR_RGB2BGR)
        else:
            img_cv = image

        gray_full = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        best_match = None
        best_score = 0.0

        for map_key, data in self._map_templates.items():
            if data is None:
                continue

            template = data["template"] if isinstance(data, dict) else data
            gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            # 模板匹配
            result = cv2.matchTemplate(gray_full, gray_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val > 0.7 and max_val > best_score:
                best_score = max_val
                best_match = map_key

        if best_match:
            display = self._map_templates[best_match].get("display_name", best_match)
            print(f"[OCR] 模板匹配到地图: {display} (相似度: {best_score:.2f})")
            return display

    def _load_map_templates(self):
        """加载地图名称模板"""
        template_dir = self.MAP_TEMPLATE_DIR

        if not os.path.exists(template_dir):
            print(f"[OCR] 地图模板目录不存在: {template_dir}")
            return

        import glob

        # 加载所有 png 文件作为模板
        # 文件名到中文名的映射（根据项目地图数据库）
        MAP_NAME_DISPLAY = {
            "qinghe": "青河镇",
            "changan": "长安城",
            "datang": "大唐官庄",
            "tianshi": "天师府",
            "fengchen": "风辰殿",
            "qinghezhen": "青河镇",
            "changancheng": "长安城",
            "datangguojing": "大唐国境",
        }

        for template_path in glob.glob(os.path.join(template_dir, "*.png")):
            filename = os.path.splitext(os.path.basename(template_path))[0]
            # 文件名作为 key，显示名作为 value
            display_name = MAP_NAME_DISPLAY.get(filename, filename)
            template = cv2.imread(template_path)
            if template is not None:
                self._map_templates[filename] = {
                    "template": template,
                    "display_name": display_name
                }
                print(f"[OCR] 加载地图模板: {filename}.png -> {display_name}")

    def register_map_template(self, map_key: str, template_image: Image.Image, display_name: str = None):
        """
        注册新的地图模板

        Args:
            map_key: 地图键名（如 "qinghe"）
            template_image: 模板图片（PIL Image）
            display_name: 显示名称（如 "青河镇"），默认为 map_key
        """
        if display_name is None:
            display_name = map_key
        self._map_templates[map_key] = {
            "template": cv2.cvtColor(
                np.array(template_image.convert('RGB')), cv2.COLOR_RGB2BGR
            ),
            "display_name": display_name
        }

    def save_map_template(self, map_key: str, image: Image.Image, region: Tuple[int, int, int, int], display_name: str = None):
        """
        从截图中裁剪并保存地图名称模板

        Args:
            map_key: 地图键名（如 "qinghe"）
            image: 完整截图
            region: 裁剪区域 (x1, y1, x2, y2)
            display_name: 显示名称（如 "青河镇"），默认为 map_key
        """
        if display_name is None:
            display_name = map_key

        template_dir = self.MAP_TEMPLATE_DIR
        os.makedirs(template_dir, exist_ok=True)

        # 裁剪模板区域
        template_img = image.crop(region)

        # 保存
        template_path = os.path.join(template_dir, f"{map_key}.png")
        template_img.save(template_path)

        # 同时注册到缓存
        self.register_map_template(map_key, template_img, display_name)

        print(f"[OCR] 保存地图模板: {template_path} -> {display_name}")

    def find_text_position(self, image: Image.Image, target: str, region: Tuple[int, int, int, int] = None) -> Optional[Tuple[int, int]]:
        """
        在图片中查找指定文字的位置

        Args:
            image: PIL Image
            target: 要查找的文字
            region: 可选，指定区域

        Returns:
            Tuple[int, int]: 文字中心点坐标 (x, y)，如果未找到返回 None
        """
        self._ensure_init()

        if isinstance(image, Image.Image):
            img = np.array(image.convert('RGB'))
        else:
            img = image

        if region:
            x1, y1, x2, y2 = region
            img = img[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
        else:
            offset_x, offset_y = 0, 0

        results = self._reader.readtext(img)

        for (bbox, text, confidence) in results:
            if target in text and confidence > 0.3:
                # 计算文字框中心点
                points = np.array(bbox)
                cx = int(np.mean(points[:, 0])) + offset_x
                cy = int(np.mean(points[:, 1])) + offset_y
                return (cx, cy)

        return None

    def read_button_text(self, image: Image.Image, region: Tuple[int, int, int, int]) -> str:
        """
        读取按钮/标签文字

        Args:
            image: PIL Image
            region: 按钮区域 (x1, y1, x2, y2)

        Returns:
            str: 识别出的文字
        """
        texts = self.read_text(image, region=region)
        return "".join(texts) if texts else ""


if __name__ == "__main__":
    # 测试
    from core.screenshot import ScreenCapture

    cap = ScreenCapture()
    cap.activate_window()
    img = cap.capture()

    ocr = OCRReader()
    map_name = ocr.read_map_name(img)
    print(f"识别到的地图名称: {map_name}")
