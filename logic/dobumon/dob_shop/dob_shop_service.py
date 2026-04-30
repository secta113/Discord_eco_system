import random
import traceback
from typing import Optional, Tuple

from core.economy import wallet
from core.utils.logger import Logger
from logic.dobumon.core.dob_logger import DobumonLogger
from logic.dobumon.core.dob_manager import DobumonManager
from logic.dobumon.core.dob_models import Dobumon
from logic.dobumon.dob_shop.dob_items import ShopItem, get_item_by_id
from logic.economy.provider import EconomyProvider


class DobumonShopService:
    """
    ドブモンショップの購入・効果適用を管理するサービス。
    """

    def __init__(self, dobumon_manager: DobumonManager):
        self.manager = dobumon_manager
        # ハンドラーの登録
        self._effect_handlers = {
            "sacrifice_mark": self._effect_next_breed_iv,
            "blood_catalyst": self._effect_next_battle_buff,
            "suicidal_drug": self._effect_suicidal_drug,
            "rotten_protein": self._effect_rotten_protein,
            "heavy_geta": self._effect_heavy_geta,
            "old_reference_book": self._effect_old_reference_book,
            "luxury_sweets": self._effect_luxury_sweets,
            "blank_scroll": self._effect_blank_scroll,
            "muscle_booster": self._effect_muscle_booster,
            "cooling_sheet": self._effect_cooling_sheet,
            "super_recovery_supple": self._effect_super_recovery_supple,
            "singularity_fragment": self._effect_next_breed_iv,
            "mutation_genome": self._effect_mutation_genome,
            "erasure_logic": self._effect_erasure_logic,
            "bad_gender_fix_m": self._effect_next_breed_gender_fix,
            "bad_gender_fix_f": self._effect_next_breed_gender_fix,
            "gender_reverse": self._effect_gender_reverse,
        }

    async def execute_purchase(
        self, user_id: int, item_id: str, dobumon_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        アイテムを購入し、効果を適用します。
        """
        item = get_item_by_id(item_id)
        if not item:
            return False, "指定されたアイテムが見つかりません。"

        # 1. 資産チェック
        balance = wallet.load_balance(user_id)
        if balance < item.price:
            return (
                False,
                f"ポイントが不足しています。（必要: {item.price} pts, 所持: {balance} pts）",
            )

        # 2. 対象ドブモンの取得（必要な場合）
        dobu = None
        if dobumon_id:
            dobu = self.manager.get_dobumon(dobumon_id)
            if not dobu:
                return False, "対象のドブモンが見つかりません。"
            if int(dobu.owner_id) != user_id:
                return False, "自分のドブモン以外にアイテムを使用することはできません。"
            if not dobu.is_alive:
                return False, "死亡しているドブモンにはアイテムを使用できません。"

            # 重複購入のチェック
            if self._is_reservation_active(dobu, item_id):
                return (
                    False,
                    "既にそのアイテムの効果が有効です。消費してから再度購入してください。",
                )

        # 3. 支払い
        try:
            EconomyProvider.escrow(user_id, item.price, reason=f"アイテム購入: {item.name}")
        except Exception as e:
            return False, f"支払いに失敗しました: {e}"

        # 4. 効果適用
        try:
            apply_success, msg = await self._apply_item_effect(user_id, item, dobu)
            if not apply_success:
                # 支払いを戻す（簡易的な補填）
                EconomyProvider.payout(user_id, item.price, reason="購入失敗による返金")
                return False, msg

            # 5. 保存
            if dobu:
                self.manager.save_dobumon(dobu)

            DobumonLogger.shop(
                "Purchase Succeeded", f"User:{user_id} Item:{item_id} Target:{dobumon_id}"
            )
            return True, msg
        except Exception as e:
            Logger.error("Shop", f"Purchase Error: {e}\n{traceback.format_exc()}")
            return False, f"エラーが発生しました: {e}"

    def _is_reservation_active(self, dobu: Dobumon, item_id: str) -> bool:
        """
        予約フラグが既に有効かチェックします。
        """
        if not dobu or not dobu.shop_flags:
            return False

        if item_id in dobu.shop_flags:
            return True

        item = get_item_by_id(item_id)
        if not item:
            return False

        if item.effect_type == "next_breed_iv" and "singularity_fragment" in dobu.shop_flags:
            return True

        return False

    async def _apply_item_effect(
        self, user_id: int, item: ShopItem, dobu: Optional[Dobumon]
    ) -> Tuple[bool, str]:
        """
        該当するハンドラーに処理を委譲します。
        """
        handler = self._effect_handlers.get(item.item_id)
        if not handler:
            return False, "未実装の効果です。"

        return await handler(dobu, item)

    # --- 効果ハンドラー群 ---

    async def _effect_next_breed_iv(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        dobu.shop_flags[item.item_id] = item.effect_value
        msg = f"「{item.name}」の秘められし力が {dobu.name} の魂に宿りました……。次なる交配の儀式にて、その神秘が解き放たれるでしょう。"
        return True, msg

    async def _effect_next_battle_buff(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        dobu.shop_flags[item.item_id] = item.effect_value
        return (
            True,
            f"禍々しき血の力が {dobu.name} の闘争本能を呼び覚まします。次なる死闘の際、その身に鬼神の如き力が宿るでしょう……！",
        )

    async def _effect_suicidal_drug(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        dobu.lifespan = max(1.0, dobu.lifespan + item.effect_value["lifespan_delta"])
        dobu.shop_flags[item.item_id] = {"train_mult": item.effect_value["train_mult"]}
        return (
            True,
            f"自らの命を燃やし尽くす覚悟…… {dobu.name} の寿命を代償に、次なる修練で限界を超える力を得るでしょう！",
        )

    async def _effect_rotten_protein(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        dobu.hp += item.effect_value["hp_bonus"]
        dobu.health += item.effect_value["hp_bonus"]
        dobu.lifespan = max(1.0, dobu.lifespan + item.effect_value["lifespan_delta"])
        return (
            True,
            f"淀んだ滋養が {dobu.name} の肉体を無理矢理に拡張させます。最大HPが上昇しましたが……その代償に命の砂時計が早まりました。",
        )

    async def _effect_heavy_geta(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        dobu.spd += item.effect_value["value"]
        dobu.lifespan = max(1.0, dobu.lifespan + item.effect_value["lifespan_delta"])
        return (
            True,
            f"過酷な負荷が {dobu.name} の肉体を限界まで研ぎ澄まします！ 圧倒的な瞬発力を得ましたが、その命は確実にすり減っています……。",
        )

    async def _effect_old_reference_book(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        from logic.dobumon.core.dob_factory import DobumonFactory

        all_attribute_skills = DobumonFactory.get_skills_by_rarity(dobu.attribute or "none")
        current_skill_names = [s["name"] for s in dobu.skills]
        possible_skills = [s for s in all_attribute_skills if s["name"] not in current_skill_names]

        if not possible_skills:
            return False, "習得可能なスキルがもうありません。"

        new_skill = random.choice(possible_skills)
        dobu.skills.append(new_skill)
        return (
            True,
            f"ページに宿る古き記憶が {dobu.name} の脳裏に閃きました！ 新たな絶技「{new_skill['name']}」を会得しました！",
        )

    async def _effect_luxury_sweets(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        dobu.affection = min(200, dobu.affection + item.effect_value["value"])
        return (
            True,
            f"甘美なる味わいに {dobu.name} の心境が和らぎました。あなたとの絆が確かなものとなったようです。",
        )

    async def _effect_blank_scroll(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        dobu.today_train_count = 0
        return (
            True,
            f"白紙の巻物が {dobu.name} の肉体の記憶を吸い取ります……。今日の疲労が幻であったかのように、再び修練への道が開かれました。",
        )

    async def _effect_muscle_booster(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        dobu.shop_flags[item.item_id] = {
            "mult": item.effect_value["mult"],
            "remaining": item.effect_value["count"],
        }
        return (
            True,
            f"沸き立つ活力が {dobu.name} の全身を駆け巡ります！ これより5度の修練において、得られる成果が飛躍的に高まるでしょう。",
        )

    async def _effect_cooling_sheet(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        dobu.shop_flags[item.item_id] = True
        return (
            True,
            f"冷涼なる安らぎが {dobu.name} の筋肉の限界を麻痺させます……。次なる修練では、成長の壁すらも超えていけるでしょう。",
        )

    async def _effect_super_recovery_supple(
        self, dobu: Dobumon, item: ShopItem
    ) -> Tuple[bool, str]:
        dobu.today_train_count = max(0, dobu.today_train_count - 3)
        dobu.lifespan = min(dobu.max_lifespan * 1.5, dobu.lifespan + item.effect_value["value"])
        return (
            True,
            f"奇跡の霊薬が {dobu.name} の肉体を再生させます！ 疲労は消え去り、命の炎さえも再び力強く燃え上がりました！",
        )

    async def _effect_mutation_genome(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        dobu.shop_flags[item.item_id] = item.effect_value
        return (
            True,
            f"未知のゲノムが {dobu.name} の遺伝子に混沌をもたらします……。次なる交配にて、狂気に満ちた突然変異の目覚めを誘発するでしょう。",
        )

    async def _effect_erasure_logic(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        """
        理の崩壊: 遺伝子(potential)を rr に書き換える。
        """
        genotype = dobu.genetics.get("genotype", {})
        if "potential" in genotype:
            genotype["potential"] = ["r", "r"]
        else:
            # 万が一スロットがない場合は作成
            genotype["potential"] = ["r", "r"]

        dobu.genetics["genotype"] = genotype
        dobu.lifespan = max(1.0, dobu.lifespan + item.effect_value["lifespan_delta"])

        return (
            True,
            f"世界の理が砕け散る……！ {dobu.name} の命を削り、その深淵たる潜在能力を強制的に『爆発』へと書き換えました……！",
        )

    def _is_forbidden_individual(self, dobu: Dobumon) -> bool:
        """禁忌の血が流れている個体かどうかを判定します。"""
        return bool(
            dobu.genetics.get("has_forbidden_red")
            or dobu.genetics.get("has_forbidden_blue")
            or "forbidden_red" in dobu.traits
            or "forbidden_blue" in dobu.traits
            or "the_forbidden" in dobu.traits
        )

    async def _effect_next_breed_gender_fix(
        self, dobu: Dobumon, item: ShopItem
    ) -> Tuple[bool, str]:
        # 禁忌チェック
        if self._is_forbidden_individual(dobu):
            return (
                False,
                "その血に刻まれた深き『禁忌』が、人為なる運命の操作を静かに拒絶しました……。",
            )

        dobu.shop_flags[item.item_id] = item.effect_value
        gender_str = "♂" if item.effect_value["gender_bias"] == "M" else "♀"
        msg = f"{dobu.name} の血肉に「{item.name}」が溶け込みました。次なる生命の灯火は、{gender_str} の形を帯びて世界に現れることでしょう……。"
        return True, msg

    async def _effect_gender_reverse(self, dobu: Dobumon, item: ShopItem) -> Tuple[bool, str]:
        # 禁忌チェック
        if self._is_forbidden_individual(dobu):
            return (
                False,
                "不可侵なる『禁忌』の血脈が生命の反転を許さず……カプセルは光を失い砕け散りました。",
            )

        old_gender = "♂" if dobu.gender == "M" else "♀"
        dobu.gender = "F" if dobu.gender == "M" else "M"
        new_gender = "♂" if dobu.gender == "M" else "♀"

        return (
            True,
            f"遺伝子の螺旋が神秘の光に包まれ…… {dobu.name} は、{old_gender} から {new_gender} へと新たな生を受け直しました！",
        )
