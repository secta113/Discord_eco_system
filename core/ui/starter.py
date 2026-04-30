import discord

from core.utils.logger import Logger
from logic.blackjack import BlackjackService, BlackjackView
from logic.chinchiro import ChinchiroService, ChinchiroView
from logic.poker.pk_service import TexasPokerService
from logic.poker.pk_view import PokerView
from managers.manager import game_manager


async def execute_game_start(interaction: discord.Interaction, session):
    # 二重開始防止のガード
    if getattr(session, "status", "") == "playing":
        Logger.info(
            "Game", f"Session {interaction.channel_id} is already playing. Skipping start message."
        )
        return
    # ゲーム種別ごとの設定マップ
    game_config = {
        "chinchiro": {"view_cls": ChinchiroView},
        "blackjack": {"view_cls": BlackjackView},
        "poker": {"view_cls": PokerView},
    }

    g_type = getattr(session, "game_type", "")
    config = game_config.get(g_type)
    if not config:
        msg = "⚠️ このゲームセッションは開始コマンドに対応していません。"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return

    # ゲームの開始処理 (Blackjack/Poker は初期化ロジックを含む)
    if hasattr(session, "start_game"):
        session.start_game()
    else:
        session.status = "playing"

    game_manager.save_session(session)

    # 共通の View 生成
    view = config["view_cls"](
        session,
        cleanup_callback=lambda: game_manager.end_session(interaction.channel_id),
        save_callback=lambda: game_manager.save_session(session),
    )

    # 初期表示処理
    p = session.get_current_player()
    if g_type == "chinchiro":
        msg = f"🎲 ゲーム開始！ 最初の番は {p['mention']} です。\n下の「🎲 振る」ボタンを押してサイコロを振ってください！"
        if interaction.response.is_done():
            await interaction.followup.send(msg, view=view)
        else:
            await interaction.response.send_message(msg, view=view)

    elif g_type == "blackjack":
        player_count = len(session.players)
        embed = discord.Embed(title="🃏 ブラックジャック 開始！", color=0x9B59B6)
        if player_count == 1:
            embed.description = "ソロモードで開始します。"
        else:
            embed.description = f"マルチモード ({player_count}人) で開始します。\n最初のターン: {p['mention'] if p else 'なし'}"

        if p:
            await view._update_display(
                interaction, f"ゲーム開始！\n{p['mention']} の番です。", is_first=True
            )
        else:
            # 全員BJ等でいきなりターン終了した場合
            d_score = session.dealer_turn()
            results = session.settle_all()
            res_text = f"ディーラーのスコア: **{d_score}**\n\n"
            for r in results:
                res_text += f"**{r['name']}** (計: {r['total_payout']}pts):\n"
                for hr in r["hands"]:
                    res_text += f"> {hr['result']}\n"
                res_text += "\n"
            await view._update_display(
                interaction,
                f"ゲーム開始直後に決着！\n\n🏆 **ゲーム終了** 🏆\n{res_text}",
                is_game_end=True,
                is_first=True,
            )

    elif g_type == "poker":
        await view.update_display(
            interaction,
            f"テキサス・ホールデム 開始！\n最初のターン: {p['mention']}",
            is_first=True,
        )
        # 初回がNPCだった場合、自動思考をキックする (Bug Fix)
        if p and p["id"] < 0:
            await view.session.process_npc_turns(view_callback=view._npc_action_callback)
            # NPCのアクション完了後に最終状態を表示
            next_p = session.get_current_player()
            if session.phase == "showdown":
                await view._finish_game(interaction)
            elif next_p:
                await view.update_display(
                    interaction, f"NPCのアクションが完了しました。<@{next_p['id']}> の番です。"
                )

    else:
        msg = "⚠️ このゲームセッションは開始コマンドに対応していません。"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
