# MHXY Agent - 梦幻西游自动任务 AI

## 项目概述
基于 MiniMax API 的梦幻西游日常任务自动化。使用视觉识别判断场景，API 负责决策，模拟输入执行动作。

## 技术架构

```
游戏画面 (模拟器/PC)
    ↓ 截图 (ADB / mss)
视觉识别 (模板匹配 + 颜色检测)
    ↓
场景分类: [战斗, 跑路, 对话, 商店, 任务菜单, 空闲]
    ↓
MiniMax API 决策 (JSON/REST)
    ↓
动作执行 (PyAutoGUI / ADB)
    ↓
循环
```

## 核心模块

### 1. screen_capture
截图模块
- `adb_screenshot()` - 安卓模拟器通过 ADB 截图
- `win_screenshot()` - Windows 客户端 mss 截图

### 2. vision
视觉识别模块
- `template_match()` - 模板匹配找按钮/图标
- `color_detect()` - 颜色检测（血条、蓝量、NPC 头顶光效）
- `scene_classifier()` - 场景分类器

### 3. game_state
游戏状态
- `GameState` - 角色信息（等级、门派、位置）
- `BattleState` - 战斗状态（我方/敌方角色信息）
- `MapState` - 地图场景

### 4. decision
决策模块
- `MiniMaxClient` - MiniMax API 调用
- `ActionPolicy` - 动作策略（攻击、防御、道具、技能）
- `TaskFlow` - 任务流程管理（师门流程、抓鬼流程等）

### 5. executor
执行模块
- `MouseExecutor` - 鼠标操作（点击、移动）
- `KeyboardExecutor` - 键盘操作（快捷键、对话）
- `AdbExecutor` - ADB 命令执行

### 6. tasks
任务流程
- `ShiMen` - 师门任务
- `ZhuaGui` - 抓鬼任务
- `副本` - 各副本流程

## 目录结构
```
mhxy-agent/
├── SKILL.md              # 本文件
├── README.md             # 项目说明
├── requirements.txt      # Python 依赖
├── config.yaml           # 配置文件
├── main.py               # 主入口
├── screen_capture/       # 截图模块
├── vision/               # 视觉识别
├── game_state/           # 游戏状态
├── decision/             # API 决策
├── executor/             # 动作执行
└── tasks/                # 任务流程
```

## 配置 (config.yaml)
```yaml
game:
  platform: android  # android | windows
  adb_serial: "127.0.0.1:5555"  # 模拟器 ADB
  window_title: "梦幻西游"  # Windows 窗口名

api:
  provider: minimax
  api_key: "${MINIMAX_API_KEY}"
  base_url: "https://api.minimax.chat/v1"

model:
  name: "MiniMax-Text-01"
  temperature: 0.7

delay:
  action: 0.3        # 动作间延迟
  battle: 1.5       # 战斗操作延迟
  random: [0.1, 0.5]  # 随机延迟范围
```

## 依赖
```
opencv-python>=4.8.0
numpy>=1.24.0
pillow>=10.0.0
mss>=9.0.1
pyyaml>=6.0
requests>=2.31.0
pyautogui>=0.9.54
```

## 安全说明
- 动作执行加随机延迟，模拟人类行为
- 不同时操作多个客户端
- 建议单开，低调使用
