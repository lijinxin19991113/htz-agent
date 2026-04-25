"""
决策模块 - MiniMax API 调用
"""
import json
import time
import random
from typing import Dict, Optional
from openai import OpenAI

from .config import Config


class DecisionMaker:
    """AI 决策类"""

    def __init__(self):
        self.cfg = Config()
        self.api_key = self.cfg.get("api.api_key")
        self.base_url = self.cfg.get("api.base_url")
        self.model = self.cfg.get("api.model")
        self.timeout = self.cfg.get("decision_timeout", 10)

        if not self.api_key:
            raise ValueError("API key 未设置，请配置 MINIMAX_API_KEY 环境变量或 config.yaml")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def decide(self, scene: str, game_state: dict, battle_info: dict = None) -> dict:
        """
        决策主入口
        返回: {"action": "attack", "target": "enemy_1", "reason": "..."}
        """
        prompt = self._build_prompt(scene, game_state, battle_info)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=256,
            )
            content = response.choices[0].message.content.strip()

            # 解析 JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content)
        except Exception as e:
            return {"action": "wait", "reason": f"API error: {e}"}

    def _system_prompt(self) -> str:
        return """你是一个梦幻西游的 AI 操作助手。

你的职责是根据当前游戏画面状态，做出最优的操作决策。

动作列表：
- attack: 普通攻击，选择目标
- skill: 使用技能，需要指定技能名和目标
- item: 使用物品，需要指定物品名
- defend: 防御
- auto: 开启自动战斗
- move: 移动到坐标
- talk: 和 NPC 对话
- menu: 打开菜单
- close: 关闭当前界面
- confirm: 确认
- wait: 等待，不要做任何动作

输出格式（必须是有效 JSON）：
{"action": "动作名", "target": "目标或坐标", "reason": "决策原因"}

注意事项：
1. 优先保证角色存活（血量低时考虑防御或吃药）
2. 师门任务优先完成
3. 战斗中选择高伤害技能集火击杀
4. 移动时注意避免卡死
"""

    def _build_prompt(self, scene: str, game_state: dict, battle_info: dict = None) -> str:
        """构建决策 Prompt"""
        lines = [f"当前场景：{scene}"]
        lines.append(f"游戏状态：{json.dumps(game_state, ensure_ascii=False)}")

        if battle_info:
            lines.append(f"战斗信息：{json.dumps(battle_info, ensure_ascii=False)}")

        lines.append("\n请做出决策。")

        return "\n".join(lines)

    def decide_battle(self, battle_info: dict, game_state: dict) -> dict:
        """战斗场景专用决策"""
        prompt = self._build_battle_prompt(battle_info, game_state)
        return self._decide(prompt)

    def _build_battle_prompt(self, battle_info: dict, game_state: dict) -> str:
        my_hp = battle_info.get("my_hp", 0)
        my_max_hp = battle_info.get("my_max_hp", 1000)
        hp_ratio = my_hp / my_max_hp if my_max_hp > 0 else 1.0

        enemies = battle_info.get("enemies", [])
        my_sect = game_state.get("sect", "unknown")

        lines = [
            f"【战斗决策】",
            f"我的门派：{my_sect}",
            f"我的血量：{my_hp}/{my_max_hp} ({hp_ratio*100:.0f}%)",
            f"敌方数量：{len(enemies)}",
        ]

        for i, enemy in enumerate(enemies):
            lines.append(f"  敌方{i+1}: {enemy.get('name', '未知')} HP: {enemy.get('hp', 0)}/{enemy.get('max_hp', 0)}")

        # 根据门派给出技能建议
        skill_advice = {
            "大唐官庄": "推荐使用【横扫千军】或普通攻击",
            "龙宫": "推荐使用【龙卷雨击】群体攻击",
            "普陀山": "优先加血或使用【灵动九天】",
            "方寸山": "可使用【失心符】控制或【定身符】",
            "狮驼岭": "可使用【变身】+【鹰击】连击",
            "阴曹地府": "可使用【阎罗令】或【尸腐毒】",
        }
        lines.append(f"\n门派建议：{skill_advice.get(my_sect, '使用普通攻击')}")

        lines.append("\n请输出战斗决策：")
        return "\n".join(lines)

    def _decide(self, prompt: str) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=256,
            )
            content = response.choices[0].message.content.strip()

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content)
        except Exception as e:
            return {"action": "wait", "reason": f"API error: {e}"}


if __name__ == "__main__":
    # 测试
    import os
    os.environ.setdefault("MINIMAX_API_KEY", "test-key")

    dm = DecisionMaker()
    result = dm.decide("战斗", {"sect": "大唐官庄", "hp": 500, "max_hp": 1000}, {
        "my_hp": 500,
        "my_max_hp": 1000,
        "enemies": [{"name": "山贼", "hp": 300, "max_hp": 500}]
    })
    print(result)
