"""
师门任务流程

任务流程：
1. 找到师门师傅 NPC（自动寻路 / 点击小地图）
2. 对话 → 接受任务
3. 判断任务类型：
   - 战斗：decide_battle() 循环直到胜利
   - 送货：找到目标 NPC，交货
   - 捕捉：使用捕捉
   - 侦察：到达指定坐标
4. 回去找师傅交任务
5. 循环 20 次
"""
import time
import logging

from core.vision import VisionResult, SceneType, BBox
from core.decision import DecisionMaker
from core.executor import Executor
from .base import BaseTask, TaskResult

logger = logging.getLogger("tasks.shimen")


class ShiMenTask(BaseTask):
    """
    师门任务

    配置（config.yaml）：
        tasks:
          shimen:
            enabled: true
            max_count: 20      # 师门次数
            master_name: "师傅"  #师傅名称（待配置）
    """

    name = "师门"

    # 师门任务类型
    TASK_TYPE = {
        "battle": "战斗",
        "deliver": "送货",
        "capture": "捕捉",
        "scout": "侦察",
    }

    def __init__(self, max_rounds: int = 20):
        super().__init__(max_rounds)
        self.task_type = None  # 当前任务类型
        self.task_target = None  # 任务目标 NPC/坐标
        self.completed = 0  # 已完成次数

    def run(self) -> TaskResult:
        """师门任务主循环"""
        logger.info(f"[师门] 开始，当前进度 {self.completed}/{self.max_rounds}")

        while self.completed < self.max_rounds:
            try:
                # 1. 找到师傅并对话
                if not self._go_to_master():
                    continue

                # 2. 接受任务
                if not self._accept_task():
                    continue

                # 3. 执行任务
                ok = self._execute_task()
                if not ok:
                    self.errors += 1
                    logger.warning(f"[师门] 任务执行失败")
                    time.sleep(2)
                    continue

                self.completed += 1
                logger.info(f"[师门] 完成 {self.completed}/{self.max_rounds}")

                # 4. 回去交任务
                self._return_and_submit()

            except Exception as e:
                self.errors += 1
                logger.error(f"[师门] 异常: {e}")
                time.sleep(2)

        return TaskResult(
            success=True,
            message=f"完成 {self.completed}/{self.max_rounds} 轮",
            rounds_completed=self.completed,
            errors=self.errors
        )

    def step(self, img, vr: VisionResult) -> bool:
        """单步执行（兼容 BaseTask 接口）"""
        return self.run() is not None

    def _go_to_master(self) -> bool:
        """
        找到师门师傅并对话
        返回 True 表示成功
        """
        logger.info(f"[师门] 寻找师傅...")

        # 策略1：点击小地图 → 自动寻路到师傅
        # 策略2：使用快捷键呼出地图 → 点击师傅位置
        # 策略3：如果已在师傅处，直接对话

        for attempt in range(3):
            img = self.cap.capture()
            vr = self.vision.classify_scene(img)

            # 如果已经在对话界面
            if vr.scene == SceneType.DIALOG:
                logger.info(f"[师门] 已在对话界面")
                return True

            # 尝试点击小地图上的师傅图标
            detections = vr.detections
            master = self.vision.find_one(detections, "npc")
            if master:
                self.exe.click(*master.to_xy_absolute(img.size[0], img.size[1]))
                time.sleep(1)
                continue

            # Fallback：按 Tab 打开大地图，搜索师傅
            self.exe.key_press(0x09)  # Tab
            time.sleep(1)

            # TODO: 大地图上的搜索逻辑
            # 目前先模拟点击师傅位置
            w, h = img.size
            self.exe.click(int(w * 0.5), int(h * 0.5))
            time.sleep(1)

        logger.warning(f"[师门] 找不到师傅")
        return False

    def _accept_task(self) -> bool:
        """
        接受师门任务
        返回 True 表示成功
        """
        logger.info(f"[师门] 接受任务...")

        # 在对话界面，等待任务提示出现
        for _ in range(10):
            img = self.cap.capture()
            vr = self.vision.classify_scene(img)

            if vr.scene != SceneType.DIALOG:
                time.sleep(0.5)
                continue

            # 查找"接受"按钮
            confirm_btn = self.vision.find_one(vr.detections, "confirm_btn")
            if confirm_btn:
                self.exe.click(*confirm_btn.to_xy_absolute(img.size[0], img.size[1]))
                time.sleep(0.5)
                return True

            # 查找对话选项（师傅会说让你去做什么）
            # TODO: 通过 OCR 读取任务内容
            # 目前假设点击第一个选项就是接受
            w, h = img.size
            self.exe.click(int(w * 0.5), int(h * 0.6))
            time.sleep(0.5)

        return False

    def _execute_task(self) -> bool:
        """
        执行任务（根据任务类型分支）
        返回 True 表示任务完成
        """
        logger.info(f"[师门] 执行任务...")

        # 识别当前任务类型
        # TODO: 需要 OCR 读取任务描述来确定类型
        # 目前默认是战斗
        self.task_type = "battle"

        if self.task_type == "battle":
            return self._execute_battle()
        elif self.task_type == "deliver":
            return self._execute_deliver()
        elif self.task_type == "capture":
            return self._execute_capture()
        elif self.task_type == "scout":
            return self._execute_scout()
        else:
            logger.warning(f"[师门] 未知任务类型: {self.task_type}")
            return False

    def _execute_battle(self) -> bool:
        """执行战斗任务"""
        logger.info(f"[师门] 战斗任务")

        battle_rounds = 0
        max_battle_rounds = 20

        while battle_rounds < max_battle_rounds:
            img = self.cap.capture()
            vr = self.vision.classify_scene(img)

            if vr.scene != SceneType.BATTLE:
                logger.info(f"[师门] 战斗结束")
                return True

            # 读取战场状态
            battle_info = vr.battle_info or {}

            # API 决策
            decision = self.decision.decide_battle(
                battle_info=battle_info,
                game_state={"sect": "unknown"}
            )

            action = decision.get("action", "wait")
            logger.info(f"[师门] 战斗决策: {action} - {decision.get('reason', '')}")

            # 执行动作
            self._execute_action(action, decision, vr, img)

            battle_rounds += 1
            time.sleep(1.5)

        logger.warning(f"[师门] 战斗超时（{max_battle_rounds} 轮）")
        return False

    def _execute_deliver(self) -> bool:
        """执行送货任务"""
        logger.info(f"[师门] 送货任务")
        # TODO: 自动寻路到目标 NPC，交货
        # 1. 读取任务目标（需要 OCR）
        # 2. 自动寻路
        # 3. 对话交货
        return True

    def _execute_capture(self) -> bool:
        """执行捕捉任务"""
        logger.info(f"[师门] 捕捉任务")
        # TODO: 找到目标，使用捕捉技能
        return True

    def _execute_scout(self) -> bool:
        """执行侦察任务"""
        logger.info(f"[师门] 侦察任务")
        # TODO: 到达指定坐标
        return True

    def _execute_action(self, action: str, decision: dict, vr: VisionResult, img):
        """执行单个战斗动作"""
        w, h = img.size

        if action == "attack":
            # 普通攻击
            attack_btn = self.vision.find_one(vr.detections, "attack_btn")
            if attack_btn:
                cx, cy = attack_btn.to_xy_absolute(w, h)
                self.exe.click(cx, cy)
                logger.info(f"[师门] 点击攻击按钮 ({cx}, {cy})")

        elif action == "skill":
            # 使用技能
            skill_name = decision.get("target", "skill_1")
            skill_btn = self.vision.find_one(vr.detections, skill_name)
            if skill_btn:
                cx, cy = skill_btn.to_xy_absolute(w, h)
                self.exe.click(cx, cy)
                logger.info(f"[师门] 点击技能 {skill_name} ({cx}, {cy})")

        elif action == "auto":
            # 自动战斗
            auto_btn = self.vision.find_one(vr.detections, "auto_btn")
            if auto_btn:
                cx, cy = auto_btn.to_xy_absolute(w, h)
                self.exe.click(cx, cy)
                logger.info(f"[师门] 开启自动战斗")

        elif action == "defend":
            defend_btn = self.vision.find_one(vr.detections, "defend_btn")
            if defend_btn:
                cx, cy = defend_btn.to_xy_absolute(w, h)
                self.exe.click(cx, cy)

        elif action == "item":
            # 使用物品（暂时不用）
            item_btn = self.vision.find_one(vr.detections, "item_btn")
            if item_btn:
                cx, cy = item_btn.to_xy_absolute(w, h)
                self.exe.click(cx, cy)

        elif action == "wait":
            # 等待，什么都不做
            pass

        else:
            logger.info(f"[师门] 未知动作: {action}")

    def _return_and_submit(self) -> bool:
        """
        回去找师傅交任务
        """
        logger.info(f"[师门] 回去交任务...")

        # 点击小地图自动寻路回去
        w, h = self.cap.capture().size

        # 点击小地图上的师傅标记（通常是顶部）
        self.exe.click(int(w * 0.9), int(h * 0.2))
        time.sleep(2)

        # 对话交任务
        for _ in range(5):
            img = self.cap.capture()
            vr = self.vision.classify_scene(img)

            if vr.scene == SceneType.DIALOG:
                # 点击确认交任务
                confirm_btn = self.vision.find_one(vr.detections, "confirm_btn")
                if confirm_btn:
                    self.exe.click(*confirm_btn.to_xy_absolute(img.size[0], img.size[1]))
                else:
                    # 没有确认按钮，点击对话框下方
                    self.exe.click(int(img.size[0] * 0.5), int(img.size[1] * 0.7))
                time.sleep(0.5)
                continue

            if vr.scene == SceneType.IDLE:
                break

            time.sleep(1)

        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    task = ShiMenTask(max_rounds=20)
    result = task.run()

    print(f"\n任务结果: {result.message}")
    print(f"成功: {result.success}")
    print(f"完成轮数: {result.rounds_completed}")
    print(f"错误次数: {result.errors}")
