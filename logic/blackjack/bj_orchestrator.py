import asyncio

from core.utils.formatters import f_pts

from .bj_deck import Deck


class BlackjackOrchestrator:
    """
    ブラックジャックのゲーム進行（ディーラーターン、結果表示等）を管理するクラス。
    UI(View)とロジック(Service)の橋渡しを行う。
    """

    def __init__(self, session):
        self.session = session

    async def handle_next_turn(
        self, interaction, update_display_func, last_action_msg, save_callback=None
    ):
        """
        次のターンに進めるか、ディーラーのターンを実行する。
        """
        has_next = self.session.advance_turn_if_needed()

        if has_next:
            if save_callback:
                save_callback()
            next_p = self.session.get_current_player()
            await update_display_func(
                interaction, f"{last_action_msg}\n次は {next_p['mention']} の番です。"
            )
        else:
            # 全員終了 -> ディーラーターン演出
            await self._run_dealer_turn(interaction, update_display_func, last_action_msg)

    async def _run_dealer_turn(self, interaction, update_display_func, last_action_msg):
        """ディーラーのドロー演出と最終決着"""
        self.session.is_dealer_turn_executed = True

        # ディーラーの裏カードを公開して一度更新
        await update_display_func(interaction, f"{last_action_msg}\nディーラーの番です。")
        await asyncio.sleep(1.0)

        # 1枚ずつ引く演出
        while self.session.should_dealer_draw():
            card_str = self.session.dealer_draw_step()
            await update_display_func(interaction, f"ディーラーがカードを引いています: {card_str}")
            await asyncio.sleep(1.2)

        # 最終決着
        results = self.session.settle_all()
        res_text = self._format_settlement_text(results)

        await update_display_func(
            interaction,
            f"🏆 **ゲーム終了** 🏆\n{res_text}",
            is_game_end=True,
        )

    def _format_settlement_text(self, results):
        """精算結果をテキスト形式に整形"""
        d_score = Deck.get_score(self.session.dealer_hand)
        res_text = f"ディーラーのスコア: **{d_score}**\n\n"
        for r in results:
            res_text += f"**{r['name']}** (計: {f_pts(r['total_payout'])}):\n"
            for hr in r["hands"]:
                res_text += f"> {hr['result']}\n"
            res_text += "\n"
        return res_text
