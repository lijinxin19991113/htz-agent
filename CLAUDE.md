# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HTZ Agent — AI 自动任务工具，用于幻唐志（回合制 MMORPG）。通过视觉识别判断场景，MiniMax API 决策下一步动作，Windows API 执行操作。

核心原则：只模拟人类操作，不做外挂作弊。

## Environment Setup

```bash
# 1. 安装 uv（如未安装）
pip install uv

# 2. 同步环境（自动安装依赖 + 创建 .venv）
uv sync

# 3. 激活虚拟环境（可选，uv run 会自动使用）
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 4. 运行项目
uv run python test_screenshot.py
```

**注意**：项目使用 Python 3.11，`.venv` 目录已通过 `.gitignore` 排除，不会提交到仓库。

## Architecture

```
游戏客户端 (Windows)
    ↓ 截图 (mss / ADB)
core/vision.py → 视觉识别 (YOLOv8 或 Fallback 模板匹配)
    ↓
core/decision.py → MiniMax API 决策 {action, target, reason}
    ↓
core/executor.py → win32api 鼠标/键盘操作
```

## Key Modules

| Module | Purpose |
|--------|---------|
| `core/screenshot.py` | 截图（Windows mss / ADB 模拟器） |
| `core/vision.py` | 视觉识别 + 场景分类（BATTLE/DIALOG/MENU/IDLE/SHOP/MAP） |
| `core/decision.py` | MiniMax API 调用，Prompt 工程 |
| `core/executor.py` | 执行鼠标点击、键盘按键、随机延迟防封 |
| `core/game_state.py` | 游戏状态管理（角色/队伍/任务进度） |
| `tasks/shimen.py` | 师门任务流程（20次循环） |

## Configuration

- 配置文件：从 `config.yaml.example` 复制为 `config.yaml`
- 窗口标题：`window_title` 需匹配游戏窗口
- API Key：环境变量 `MINIMAX_API_KEY`
- 平台：`game.platform: windows` 或 `android`

## Known Limitations

1. **YOLOv8 未训练** — vision.py 默认 Fallback 模式，精度有限；需采集标注数据后训练 `assets/weights/htz.pt`
2. **无 OCR** — 暂无法读取文字（任务描述、血量数值）
3. **无自动寻路** — 地图坐标需手动定义
4. **防封策略简单** — 仅随机延迟，高频使用有风险

## Data Flow (for Battle)

```
screenshot → vision.classify_scene() → SceneType.BATTLE + BattleInfo
                ↓
decision.decide_battle(battle_info, game_state) → {"action": "skill", "target": "enemy_1"}
                ↓
executor.click(x, y)  # 带 0.3-1.5s 随机延迟
```

## Task Flow (师门)

```
找师傅 → 对话接受任务 → 循环20次 [战斗/送货/捕捉/侦察] → 交任务领奖励
```

战斗决策会根据门派（dt/fm/lg/pt/df/st）推荐技能。