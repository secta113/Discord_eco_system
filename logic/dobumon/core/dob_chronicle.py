import random
from typing import Dict

from core.handlers.storage import IDobumonRepository
from logic.dobumon.core.dob_logger import DobumonLogger
from logic.dobumon.core.dob_models import Dobumon


class DobumonChronicle:
    """
    ドブモンの時間経過（加齢、寿命、死亡イベント）に関連する処理を担当するクラス。
    """

    def __init__(self, repo: IDobumonRepository, handle_death_fn, save_fn):
        self.repo = repo
        self.handle_death = handle_death_fn
        self.save_dobumon = save_fn

    def process_natural_aging(self) -> Dict:
        """
        全生存個体の自然加齢（寿命-1）と、晩年期の突然死判定を行います。
        1日1回実行される想定です。
        """
        # DBから全生存個体を取得
        all_alive_models = self.repo.get_all_alive_dobumons()
        affected_count = 0
        death_count = 0

        for model in all_alive_models:
            dobu = Dobumon(**model.model_dump())
            # 寿命消費倍率 (モデルで一括計算)
            consumption_mod = dobu.consumption_mod

            # 寿命消費 (基本 1.0)
            old_life = dobu.lifespan

            dobu.lifespan = max(0.0, dobu.lifespan - (1.0 * consumption_mod))

            DobumonLogger.aging(dobu, old_life, dobu.lifespan, consumption_mod)

            # 突然死判定
            dead = False
            if dobu.lifespan <= 0:
                dead = True
            else:
                # 突然死リスクの計算 (ベース緩和版)
                risk_prob = 0.0
                if dobu.life_stage == "twilight":
                    risk_prob += 0.02  # 0.05 -> 0.02 に緩和

                # 健康リスク (係数Fによる上昇: F=0.25 で 5% / 禁忌深度は 2% 加算)
                inbreeding_f = dobu.genetics.get("inbreeding_debt", 0.0)
                forbidden_depth = dobu.genetics.get("forbidden_depth", 0.0)
                risk_prob += (inbreeding_f * 0.20) + (forbidden_depth * 0.02)

                # 絆によるリスク補正
                if dobu.affection < 0:
                    risk_prob += 0.02
                elif dobu.affection < 5:
                    risk_prob += 0.01
                elif dobu.affection >= 100:
                    risk_prob -= 0.03
                elif dobu.affection >= 50:
                    risk_prob -= 0.01

                # 確率は 0% 未満にはならない
                risk_prob = max(0.0, risk_prob)

                if random.random() < risk_prob:
                    dead = True

            if dead:
                if self.handle_death(dobu, "Natural Aging / Sudden Death"):
                    death_count += 1

            self.save_dobumon(dobu)
            affected_count += 1

        return {"affected": affected_count, "deaths": death_count}
