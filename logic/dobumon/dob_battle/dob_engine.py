import math
import random
from typing import Dict, List, Optional

from core.utils.logger import Logger
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_battle.dob_calculator import BattleCalculator
from logic.dobumon.training import get_skill_template


class BattleEngine:
    """
    怒武者の戦闘進行を管理するエンジン。
    Time-Skip型のATB（Active Time Battle）を実現します。
    """

    def __init__(self, dobu1: Dobumon, dobu2: Dobumon):
        self.dobu1 = dobu1
        self.dobu2 = dobu2
        self.steps = []
        self.calc = BattleCalculator()

    def get_attr_emoji(self, attr: str) -> str:
        return {"fire": "🔥", "water": "💧", "grass": "🌿"}.get(attr, "❓")

    def select_action(self, attacker: Dobumon) -> Dict:
        """
        行動（スキル）を選択します。
        とりあえずランダムですが、技があれば技を使います。
        """
        if not attacker.skills:
            return {"name": "通常の攻撃", "power": 50, "accuracy": 100, "type": "damage"}

        # 技を習得している場合、30%の確率で技を使う
        if random.random() < 0.3:
            skill_data = random.choice(attacker.skills)
            template = get_skill_template(skill_data["template_id"])
            if template:
                return {
                    "name": skill_data["name"],
                    "power": template.power if template.effect_type == "damage" else 0,
                    "accuracy": template.accuracy,
                    "type": template.effect_type,
                    "template": template,
                }

        return {"name": "通常の攻撃", "power": 50, "accuracy": 100, "type": "damage"}

    def simulate(self) -> Dict:
        """戦闘をシミュレーションします（Time-Skip ATB）"""
        hp1 = self.dobu1.health if self.dobu1.health > 0 else self.dobu1.hp
        hp2 = self.dobu2.health if self.dobu2.health > 0 else self.dobu2.hp

        Logger.info(
            "Dobumon", f"Battle Start: {self.dobu1.name} (HP:{hp1}) vs {self.dobu2.name} (HP:{hp2})"
        )

        # 行動までの待機ゲージ (100で行動可能)
        timer1 = 100.0 - random.uniform(0, 10)
        timer2 = 100.0 - random.uniform(0, 10)

        # 行動回数による疲労度 (SPD減衰用)
        fatigue_count1 = 0
        fatigue_count2 = 0

        turn_count = 0
        total_time = 0.0

        self.steps.append(
            {
                "turn": 0,
                "p1_hp": hp1,
                "p2_hp": hp2,
                "attacker": None,
                "damage": 0,
                "action": "戦闘開始",
                "is_skill": False,
            }
        )

        while hp1 > 0 and hp2 > 0 and turn_count < 100:
            # 現在の実効行動力を計算 (SPD * 0.98^行動回数)
            current_spd1 = max(1.0, self.dobu1.spd * pow(0.98, fatigue_count1))
            current_spd2 = max(1.0, self.dobu2.spd * pow(0.98, fatigue_count2))

            # 次に誰かが動けるようになるまでの時間を計算
            wait1 = timer1 / current_spd1
            wait2 = timer2 / current_spd2

            jump = min(wait1, wait2)
            total_time += jump

            # 全員のタイマーを減らす
            timer1 -= jump * current_spd1
            timer2 -= jump * current_spd2

            # 行動者の特定
            actors = []
            if timer1 <= 0.001:
                actors.append(1)
                timer1 = 100.0
                fatigue_count1 += 1
            if timer2 <= 0.001:
                actors.append(2)
                timer2 = 100.0
                fatigue_count2 += 1

            # 同時行動の場合はランダム（またはSPD判定だが既にジャンプで解決済み）
            random.shuffle(actors)

            for actor_id in actors:
                if hp1 <= 0 or hp2 <= 0:
                    break
                turn_count += 1

                attacker = self.dobu1 if actor_id == 1 else self.dobu2
                defender = self.dobu2 if actor_id == 1 else self.dobu1

                action = self.select_action(attacker)

                # 命中判定
                is_hit = self.calc.check_hit(attacker, defender, action.get("accuracy", 100))

                dmg = 0
                is_crit = False
                msg = action["name"]

                if is_hit:
                    if action["type"] == "damage":
                        res = self.calc.calculate_damage(attacker, defender, action["power"])
                        dmg = res["damage"]
                        is_crit = res["is_critical"]

                        if is_crit:
                            msg += "（クリティカル！）"
                        if res["attr_multiplier"] > 1.0:
                            msg += "（効果はばつぐんだ！）"
                        elif res["attr_multiplier"] < 1.0:
                            msg += "（効果はいまひとつのようだ…）"
                    else:
                        # バフ等の特殊効果は一旦メッセージのみ
                        msg += "（効果を発動した！）"
                else:
                    msg += "（しかし、攻撃は外れた！）"

                if actor_id == 1:
                    hp2 = max(0, hp2 - dmg)
                else:
                    hp1 = max(0, hp1 - dmg)

                self.steps.append(
                    {
                        "turn": turn_count,
                        "p1_hp": int(math.ceil(hp1)),
                        "p2_hp": int(math.ceil(hp2)),
                        "attacker": actor_id,
                        "damage": int(dmg),
                        "hit": is_hit,
                        "action": msg,
                        "is_skill": action["name"] != "通常の攻撃",
                    }
                )

        winner_id = None
        if hp1 > 0 and hp2 <= 0:
            winner_id = self.dobu1.dobumon_id
        elif hp2 > 0 and hp1 <= 0:
            winner_id = self.dobu2.dobumon_id

        return {
            "winner_id": winner_id,
            "loser_id": self.dobu2.dobumon_id
            if winner_id == self.dobu1.dobumon_id
            else (self.dobu1.dobumon_id if winner_id == self.dobu2.dobumon_id else None),
            "steps": self.steps,
            "turns": turn_count,
            "total_time": total_time,
            "p1_remaining_hp": hp1,
            "p2_remaining_hp": hp2,
        }
