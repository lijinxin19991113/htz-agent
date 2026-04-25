# HTZ Agent - AI 开发助手交接文档

> 本文档面向接手本项目的 AI Agent，详细记录项目背景、技术方案、待完成工作、已知问题。
> 如有疑问，先查本文档，再查 SPEC.md 和 SKILL.md。

---

## 一、项目背景

**项目名称**：HTZ Agent（幻唐志 AI 自动任务）
**目标**：全自动完成幻唐志日常任务（师门、抓鬼、副本等）
**技术路线**：视觉识别（YOLOv8）+ MiniMax API 决策 + Windows API 执行
**平台**：Windows PC 客户端
**代码路径**：`~/developtool/projects/htz-agent/`

---

## 二、技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                     游戏客户端 (Windows)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ mss 截图
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  vision.py                                                     │
│  • YOLOv8 检测 → BBox 列表（UI按钮/NPC/怪物/血条）            │
│  • 场景分类 → SceneType (BATTLE/DIALOG/MENU/IDLE/SHOP/MAP)  │
│  • 归一化坐标输出，不依赖固定分辨率                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            ▼                              ▼
┌─────────────────────┐      ┌─────────────────────┐
│   decision.py        │      │   game_state.py     │
│   MiniMax API 决策   │      │   游戏状态管理      │
│   Prompt 工程        │      │   角色/队伍/任务    │
└──────────┬──────────┘      └─────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│  executor.py                                                   │
│  win32api 鼠标键盘操作                                         │
│  随机延迟防封                                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、目录结构

```
htz-agent/
├── agents.md           # 本文件（AI 交接文档）
├── SPEC.md             # 详细技术方案
├── SKILL.md            # 项目说明
├── README.md           # 使用说明（待写）
├── requirements.txt    # Python 依赖
├── config.yaml         # 配置文件
│
├── core/               # 核心模块
│   ├── __init__.py
│   ├── config.py       # ✅ 配置加载（YAML + 环境变量）
│   ├── screenshot.py  # ✅ 截图（mss Windows / ADB 安卓）
│   ├── vision.py       # ✅ YOLOv8 检测 + 场景分类
│   ├── decision.py     # ✅ MiniMax API 决策
│   ├── executor.py     # ✅ Windows 鼠标键盘执行
│   ├── game_state.py   # ✅ 游戏状态管理
│
├── tasks/              # 任务流程
│   ├── __init__.py
│   ├── base.py         # ✅ 任务基类
│   ├── shimen.py      # ✅ 师门任务流程
│   ├── zhuagui.py     # ⏳ 抓鬼任务（待实现）
│   └── fuben.py       # ⏳ 副本（待实现）
│
├── assets/
│   ├── templates/       # 模板图片（备选，暂时用 YOLOv8）
│   └── weights/         # YOLOv8 模型权重
│       └── htz.pt     # ⏳ 待训练
│
├── logs/               # 运行日志
└── data/                # 标注数据（Roboflow 格式）
```

---

## 四、核心模块详解

### 4.1 vision.py（已完成）

**类**：`Vision`、`YOLOv8Detector`、`BBox`、`BattleInfo`、`VisionResult`

**YOLOv8 检测类别**（classes.txt，需要训练后确认）：
```
attack_btn, skill_btn, item_btn, defend_btn,
confirm_btn, cancel_btn, auto_btn,
hp_bar, mp_bar,
enemy, ally, npc, monster,
dialog, menu, shop, map
```

**输出归一化坐标**（0-1 范围）：
```python
@dataclass
class BBox:
    class_name: str
    confidence: float
    x1, y1, x2, y2: float  # 归一化

# 使用示例
detections = vision.detect(image)
for det in detections:
    cx, cy = det.to_xy_absolute(screen_w, screen_h)  # 转绝对坐标
    x1, y1, x2, y2 = det.to_absolute(screen_w, screen_h)
```

**场景分类**：
```python
result = vision.classify_scene(image)
result.scene      # SceneType 枚举
result.confidence # float 0-1
result.detections # List[BBox]
result.battle_info # BattleInfo（如果在战斗中）
```

**初始化**：
```python
vision = Vision(yolo_model_path=None, use_cuda=True)
# 如果 yolo_model_path 为 None，会自动寻找 assets/weights/htz.pt
# 如果模型不存在或加载失败，自动降级到 Fallback 模式
```

---

### 4.2 decision.py（已完成）

**类**：`DecisionMaker`

**初始化**（需要 API Key）：
```python
# 方式1: 环境变量
# export MINIMAX_API_KEY="your-key"

# 方式2: 直接传入
dm = DecisionMaker()
```

**决策接口**：
```python
# 普通场景决策
result = dm.decide(
    scene="师门-对话",
    game_state={"sect": "大唐官庄", "hp": 800, "max_hp": 1000},
    battle_info=None
)
# 返回: {"action": "talk", "target": "师傅", "reason": "..."}

# 战斗场景决策
result = dm.decide_battle(
    battle_info={"my_hp": 800, "my_max_hp": 1000, "enemies": [...]},
    game_state={"sect": "大唐官庄"}
)
```

**支持的 Action**：
```
attack, skill, item, defend, auto,
move, talk, menu, close, confirm, wait
```

---

### 4.3 executor.py（已完成）

**类**：`Executor`

**初始化**（需要游戏窗口在前台）：
```python
exe = Executor()  # 自动查找 config.yaml 中的 window_title
```

**常用方法**：
```python
# 鼠标操作
exe.click(x, y)           # 左键点击
exe.right_click(x, y)     # 右键点击
exe.double_click(x, y)     # 双击
exe.drag(x1, y1, x2, y2)  # 拖拽

# 键盘操作
exe.key_press(key_code)    # 按键（需要 win32con.VK_* 常量）
exe.press_esc()           # ESC
exe.press_enter()         # 回车
exe.type_text("hello")    # 输入文字（英文）

# 窗口
exe.activate_window()     # 激活游戏窗口
exe.get_window_rect()     # 获取窗口坐标
```

**防封延迟**：所有操作自动加 0.3-1.5 秒随机延迟

---

### 4.4 screenshot.py（已完成）

**类**：`ScreenCapture`

```python
cap = ScreenCapture()

# Windows 截图
img = cap.win_screenshot()  # 需要 pywin32 + mss

# ADB 截图（安卓模拟器）
img = cap.adb_screenshot()

# 统一接口（根据 config.yaml 自动选择）
img = cap.capture()

# 保存
cap.save(img, "/tmp/screenshot.png")
```

---

### 4.5 config.py（已完成）

```python
from core.config import Config
cfg = Config()

cfg.get("game.platform")          # "windows"
cfg.get("game.window_title")      # "幻唐志"
cfg.get("api.api_key")            # 从环境变量读取
cfg.get("delay.action")           # 0.3
cfg.resolution                    # {"width": 960, "height": 540}
```

---

## 五、待完成任务

### 5.1 YOLOv8 模型训练（关键路径）

**步骤**：
1. 采集 50-100 张游戏截图（不同场景：战斗、对话、菜单、跑路等）
2. 用 LabelImg 标注，保存为 YOLO TXT 格式
3. 编写 `dataset.yaml`：
   ```yaml
   path: ./data
   train: images/train
   val: images/val
   names: ["attack_btn", "skill_btn", "enemy", "npc", ...]
   ```
4. 训练：
   ```python
   from ultralytics import YOLO
   model = YOLO("yolov8n.pt")
   model.train(data="dataset.yaml", epochs=50, imgsz=640)
   ```
5. 导出权重到 `assets/weights/htz.pt`

**标注优先级**：
1. `attack_btn`, `confirm_btn`（最高频）
2. `hp_bar`, `mp_bar`, `enemy`
3. `npc`, `dialog`
4. 其他 UI 元素

### 5.2 game_state.py（待实现）

管理游戏运行时状态：
```python
@dataclass
class GameState:
    role_name: str      # 角色名
    level: int          # 等级
    sect: str           # 门派
    hp: int; max_hp: int
    mp: int; max_mp: int
    money: int          # 银两
    current_map: str     # 当前地图
    task_progress: dict  # 当前任务进度
```

### 5.3 tasks/shimen.py（待实现）

师门任务流程（20次循环）：
```
1. 自动寻路到师门师傅
2. 对话 → 接受任务
3. 判断任务类型：
   - 战斗：调用 decision.decide_battle() 循环直到胜利
   - 送货：自动寻路到目标 NPC，交货
   - 捕捉：使用捕捉技能
   - 侦察：到达指定坐标
4. 回去交任务
5. 循环直到 20 次
```

### 5.4 tasks/zhuagui.py（待实现）

抓鬼任务流程（10只循环）：
```
1. 组队（或单刷）
2. 找到钟馗（长安城）
3. 接受任务，获取鬼位置
4. 自动寻路到鬼坐标
5. 检测到鬼 → 进入战斗 → decide_battle()
6. 循环 10 只
7. 回去交任务
```

---

## 六、已知限制

1. **YOLOv8 未训练**：目前 vision.py 使用传统方法 Fallback，精度有限
2. **无 OCR**：暂时无法读取文字（任务描述、血量数值）
3. **无自动寻路**：地图坐标需要手动定义或后期接入
4. **防封策略简单**：仅靠随机延迟，高频使用仍有风险
5. **单开限制**：不支持同时操作多个客户端

---

## 七、配置文件参考

`config.yaml` 关键配置项：
```yaml
game:
  platform: windows          # android | windows
  window_title: "幻唐志"    # 游戏窗口标题（需确认）
  # 分辨率（自动检测，可不填）
  # resolution:
  #   width: 1920
  #   height: 1080

api:
  provider: minimax
  api_key: "${MINIMAX_API_KEY}"  # 环境变量方式
  base_url: "https://api.minimax.chat/v1"
  model: "MiniMax-Text-01"

delay:
  action: 0.3
  random_min: 0.1
  random_max: 0.5

anti_ban:
  enabled: true
  max_continuous_runtime: 3600
```

---

## 八、依赖清单

```
# 核心
opencv-python>=4.8.0
pillow>=10.0.0
numpy>=1.24.0

# YOLOv8
ultralytics>=8.0.0

# Windows 操作
mss>=9.0.1
pywin32>=306

# API
openai>=1.12.0
requests>=2.31.0

# 配置
pyyaml>=6.0
python-dotenv>=1.0.0
```

---

## 九、快速开始

```bash
# 1. 安装依赖
cd ~/developtool/projects/htz-agent
pip install -r requirements.txt

# 2. 确认 config.yaml
# - window_title 填你的游戏窗口标题
# - MINIMAX_API_KEY 环境变量

# 3. 训练 YOLOv8（可选，Fallback 模式也能跑）
# 见 5.1 节

# 4. 测试截图
python -c "from core.screenshot import ScreenCapture; cap = ScreenCapture(); img = cap.capture(); print(img.size)"

# 5. 测试视觉识别
python -c "from core.vision import Vision; v = Vision(); print(v.use_yolo)"

# 6. 运行师门任务
python -c "from tasks.shimen import run; run()"
```

---

## 十、调试技巧

```python
# 打印所有检测结果
result = vision.classify_scene(img)
for det in result.detections:
    print(f"{det.class_name}: conf={det.confidence:.2f} bbox={det.x1:.2f},{det.y1:.2f}-{det.x2:.2f},{det.y2:.2f}")

# 保存带标注的截图
import cv2
for det in result.detections:
    x1,y1,x2,y2 = det.to_absolute(img.shape[1], img.shape[0])
    cv2.rectangle(img, (x1,y1), (x2,y2), (0,255,0), 2)
cv2.imwrite("/tmp/annotated.png", img)
```

---

## 十一、后续扩展方向

1. **多账号管理**：支持切换账号
2. **副本自动化**：大闹天宫、通天等副本流程
3. **物品管理**：自动卖垃圾、存仓库
4. **本地模型替代 API**：Llama 本地推理降低 API 成本
5. **强化学习训练**：长期目标是 RL 自学习策略
