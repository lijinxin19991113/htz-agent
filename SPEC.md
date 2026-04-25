# HTZ Agent - 详细技术方案

## 一、项目概述

**目标**：全自动完成梦幻西游日常任务（师门、抓鬼、副本），基于视觉识别 + MiniMax API 决策。

**核心思路**：不做外挂作弊，只模拟人类操作，通过 AI 判断当前场景 + 决定下一步动作。

---

## 二、技术架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    游戏客户端                            │
│         (安卓模拟器 / PC Windows)                        │
└────────────────┬────────────────────────────────────────┘
                 │ 截图
                 ▼
┌─────────────────────────────────────────────────────────┐
│              screen_capture 截图模块                      │
│     ADB / mss / Window API  →  PIL Image                │
└────────────────┬────────────────────────────────────────┘
                 │ 图像帧
                 ▼
┌─────────────────────────────────────────────────────────┐
│               vision 视觉识别模块                         │
│   模板匹配 + 颜色检测 + 场景分类                          │
│   输出: scene_type + ui_elements + game_data            │
└────────────────┬────────────────────────────────────────┘
                 │ 状态描述
                 ▼
┌─────────────────────────────────────────────────────────┐
│              decision 决策模块                            │
│   MiniMax API → {action, target, args}                   │
│   Action: [attack, skill, item, move, talk, menu]       │
└────────────────┬────────────────────────────────────────┘
                 │ 动作指令
                 ▼
┌─────────────────────────────────────────────────────────┐
│              executor 执行模块                            │
│   PyAutoGUI / ADB / Windows API → 鼠标键盘操作            │
└─────────────────────────────────────────────────────────┘
```

---

## 三、游戏平台选择

**推荐安卓模拟器**，原因：
- 截图稳定（ADB screenshot）
- 多开方便
- 模拟器分辨率固定，模板匹配稳定
- 不影响 PC 日常使用

**推荐模拟器**：雷电模拟器（兼容性好）

---

## 四、视觉识别方案

### 4.1 截图方式

**安卓模拟器（雷电）**：
```python
import subprocess
def adb_screenshot(serial="127.0.0.1:5555"):
    subprocess.run(["adb", "-s", serial, "exec-out", "screencap", "-p"],
                   stdout=open("/tmp/screen.png", "wb"))
    return Image.open("/tmp/screen.png")
```

**Windows PC 端**：
```python
import mss
def win_screenshot(hwnd):
    # 使用 mss + win32 API 获取窗口截图
    pass
```

### 4.2 场景识别

通过**模板匹配 + 颜色特征**识别当前场景：

| 场景 | 识别特征 | 检测方式 |
|------|---------|---------|
| 战斗 | 血条、敌方头像、速度条 | 颜色：红色血条、绿色蓝量 |
| 跑路 | 地图、坐标、任务追踪 | 模板：地图图标 |
| NPC对话 | 对话窗口、选项按钮 | 模板：对话框、选项按钮 |
| 物品/商店 | 背包图标、商品标签 | 颜色 + 模板 |
| 师门菜单 | 师门任务进度条 | 文字识别（OCR）/ 颜色 |
| 空闲 | 无明显特征 | 排除法 |

### 4.3 关键 UI 元素检测

**按钮点击区域**（相对坐标，按屏幕比例）：
```python
# 960x540 虚拟分辨率下的按钮位置（按比例）
BUTTON_POS = {
    "attack": (0.85, 0.75),      # 攻击按钮
    "skill_1": (0.75, 0.80),      # 技能1
    "skill_2": (0.80, 0.80),      # 技能2
    "item": (0.70, 0.75),         # 物品
    "defend": (0.65, 0.75),      # 防御
    "auto": (0.90, 0.55),         # 自动战斗
    "confirm": (0.50, 0.70),     # 确认
    "cancel": (0.40, 0.70),      # 取消
    "close": (0.90, 0.10),       # 关闭
    "menu": (0.10, 0.85),        # 菜单
    "map": (0.90, 0.20),         # 地图
}
```

**颜色检测关键点**：
- 血条：`RGB(255, 50, 50)` 附近
- 蓝量：`RGB(50, 150, 255)` 附近
- NPC 头顶黄点：`RGB(255, 200, 50)` 附近
- 战斗开始：`RGB(255, 255, 200)` 附近

### 4.4 文字识别（OCR）

用于读取：
- 任务描述
- 角色等级/门派
- 物品名称
- 剧情对话

**推荐方案**：EasyOCR（支持中文，轻量）

---

## 五、决策系统（MiniMax API）

### 5.1 API 调用设计

```python
class MiniMaxClient:
    def __init__(self, api_key, base_url="https://api.minimax.chat/v1"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def decide(self, scene: str, battle_info: dict, game_state: dict) -> dict:
        prompt = f"""你是一个梦幻西游的 AI 操作助手。
当前场景：{scene}
游戏状态：{json.dumps(game_state, ensure_ascii=False)}
战斗信息：{json.dumps(battle_info, ensure_ascii=False)}

根据当前情况，选择一个最优动作：
动作列表：
- attack: 普通攻击
- skill_1 ~ skill_5: 使用技能（需指定技能名）
- item: 使用物品（需指定物品名）
- defend: 防御
- auto: 开启自动战斗
- move: 移动到坐标
- talk: 和 NPC 对话
- menu: 打开菜单

输出 JSON：
{{"action": "动作名", "target": "目标", "reason": "原因"}}
"""
        response = self.client.chat.completions.create(
            model="MiniMax-Text-01",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return json.loads(response.choices[0].message.content)
```

### 5.2 场景决策 Prompt 示例

**师门任务场景**：
```
当前场景：师门任务 - 战斗
角色：75级 大唐官庄 门派
我方：1人（满血满蓝）
敌方：山贼 x3（血量各剩50%）
任务进度：3/20

请决策下一步动作。
```

**抓鬼场景**：
```
当前场景：抓鬼 - 跑路
小地图显示：长寿村野外（60,35）
任务追踪：点击自动寻路到("20,10")
我方：5人队伍，全部满状态

请决策下一步动作。
```

---

## 六、任务流程

### 6.1 师门任务流程

```
开始
  ↓
找师傅（点击师门师傅 / 自动寻路）
  ↓
对话 → 接受任务
  ↓
循环直到20次
  ┌─────────────────────────┐
  │ 判断任务类型：             │
  │ 1. 战斗 → 自动打          │
  │ 2. 送货 → 找到NPC交货      │
  │ 3. 捕捉 → 使用捕捉技能    │
  │ 4. 侦察 → 找到坐标        │
  └─────────────────────────┘
  ↓
回去交任务
  ↓
领取奖励，判断是否继续
```

### 6.2 抓鬼流程

```
开始
  ↓
组队（如果单开则自动组队，或单刷）
  ↓
找到钟馗（长安城）
  ↓
接受任务，获取鬼位置
  ↓
自动寻路到鬼坐标
  ↓
检测到鬼 → 进入战斗
  ↓
循环 10 只鬼
  ↓
回去交任务
```

### 6.3 战斗流程

```
检测战斗开始
  ↓
读取战场信息（我方/敌方状态）
  ↓
MiniMax API 决策（考虑：门派、敌我血量、场局势）
  ↓
执行动作（攻击/技能/道具）
  ↓
等待动画（1-2秒）
  ↓
检测是否结束
  ↓
未结束 → 继续决策
结束 → 退出战斗 → 继续任务
```

---

## 七、执行模块

### 7.1 ADB 执行（安卓模拟器）

```python
import subprocess

class AdbExecutor:
    def __init__(self, serial="127.0.0.1:5555"):
        self.serial = serial

    def tap(self, x, y):
        """点击坐标"""
        subprocess.run(["adb", "-s", self.serial, "shell", "input", "tap", str(x), str(y)])

    def swipe(self, x1, y1, x2, y2, duration=500):
        """滑动"""
        subprocess.run(["adb", "-s", self.serial, "shell", "input", "swipe",
                        str(x1), str(y1), str(x2), str(y2), str(duration)])

    def text(self, content):
        """输入文字"""
        subprocess.run(["adb", "-s", self.serial, "shell", "input", "text", content])
```

### 7.2 PyAutoGUI 执行（PC端）

```python
import pyautogui

class WinExecutor:
    def tap(self, x, y, duration=0.1):
        pyautogui.click(x, y, duration=duration)

    def swipe(self, x1, y1, x2, y2, duration=0.5):
        pyautogui.moveTo(x1, y1, duration=0.1)
        pyautogui.drag(x2-x1, y2-y1, duration=duration)
```

### 7.3 随机延迟（防封）

```python
import random
import time

def human_delay(min_sec=0.3, max_sec=1.5):
    """模拟人类操作延迟"""
    time.sleep(random.uniform(min_sec, max_sec))

def human_move(from_pos, to_pos):
    """人类轨迹移动（带弧度）"""
    mx = (from_pos[0] + to_pos[0]) / 2 + random.randint(-50, 50)
    my = (from_pos[1] + to_pos[1]) / 2 - random.randint(20, 80)
    # pyautogui.moveTo(from_pos, duration=0.2)
    # pyautogui.moveTo((mx, my), duration=0.15)
    # pyautiyui.moveTo(to_pos, duration=0.2)
```

---

## 八、实现步骤（Roadmap）

### Phase 1：基础设施（1-2天）
- [ ] 项目架子搭建（已完成）
- [ ] 截图模块（ADB / mss）
- [ ] 基础视觉识别（模板匹配）
- [ ] API 客户端封装

### Phase 2：场景识别（2-3天）
- [ ] 场景分类器
- [ ] 战斗状态读取（血条/蓝量/敌我识别）
- [ ] 地图坐标读取
- [ ] OCR 集成（EasyOCR）

### Phase 3：决策系统（2-3天）
- [ ] MiniMax API Prompt 工程
- [ ] 各场景决策逻辑
- [ ] 动作执行器

### Phase 4：任务流程（3-5天）
- [ ] 师门任务（20次循环）
- [ ] 抓鬼任务（10只循环）
- [ ] 副本流程

### Phase 5：调优（持续）
- [ ] 识别率优化
- [ ] 决策 Prompt 优化
- [ ] 防封策略

---

## 九、文件结构

```
htz-agent/
├── SKILL.md              # 技能文档
├── SPEC.md               # 本文件 - 详细技术方案
├── README.md             # 使用说明
├── requirements.txt      # Python 依赖
├── config.yaml           # 配置文件
├── main.py               # 主入口
│
├── core/                 # 核心模块
│   ├── __init__.py
│   ├── config.py         # 配置加载
│   ├── screenshot.py     # 截图模块
│   ├── vision.py         # 视觉识别
│   ├── decision.py       # API 决策
│   └── executor.py       # 动作执行
│
├── tasks/                # 任务流程
│   ├── __init__.py
│   ├── shimen.py         # 师门
│   ├── zhuagui.py        # 抓鬼
│   └── fuben.py          # 副本
│
├── assets/               # 资源文件
│   ├── templates/        # 模板图片
│   │   ├── attack_btn.png
│   │   ├── skill_btn.png
│   │   ├── npc_dialog.png
│   │   └── ...
│   └── positions.yaml    # 按钮位置配置
│
└── logs/                 # 运行日志
```

---

## 十、依赖清单

```
# 视觉 & 图像处理
opencv-python>=4.8.0
pillow>=10.0.0
numpy>=1.24.0

# OCR（可选）
easyocr>=1.7.0

# 截图（Windows）
mss>=9.0.1
pywin32>=306      # Windows API

# 操作模拟
pyautogui>=0.9.54

# API
requests>=2.31.0
openai>=1.12.0     # MiniMax 兼容 OpenAI SDK

# 配置
pyyaml>=6.0

# 工具
python-dotenv>=1.0.0
```

---

## 十一、注意事项

### 防封建议
1. **随机延迟**：所有操作加 0.3-1.5 秒随机延迟
2. **轨迹模拟**：移动带弧度，不走直线
3. **单开原则**：不同时操作多个客户端
4. **低频运行**：避免 24 小时连续跑
5. **异常检测**：多次失败后自动停止

### 风险声明
- 本项目仅供个人学习研究
- 梦幻西游有多开检测机制，使用本工具需自行承担风险
- 建议先用小号测试，确认安全后再用于主号
