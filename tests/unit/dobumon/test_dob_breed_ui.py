from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from logic.dobumon.dob_views.dob_breeding import BreedSelectView


@pytest.mark.asyncio
async def test_breed_select_view_taboo_logic():
    """BreedSelectView の同性交配（禁忌）メッセージ表示ロジックをテスト"""
    from logic.dobumon.core.dob_models import Dobumon

    user = MagicMock(spec=discord.User)
    user.id = 123

    # 準備：オス2体、メス1体
    dobu_m1 = MagicMock(spec=Dobumon)
    dobu_m1.dobumon_id = "M1"
    dobu_m1.name = "オス1"
    dobu_m1.gender = "M"
    dobu_m1.lineage = []
    dobu_m1.genetics = {}

    dobu_m2 = MagicMock(spec=Dobumon)
    dobu_m2.dobumon_id = "M2"
    dobu_m2.name = "オス2"
    dobu_m2.gender = "M"
    dobu_m2.lineage = []
    dobu_m2.genetics = {}

    dobu_f1 = MagicMock(spec=Dobumon)
    dobu_f1.dobumon_id = "F1"
    dobu_f1.name = "メス1"
    dobu_f1.gender = "F"
    dobu_f1.lineage = []
    dobu_f1.genetics = {}

    dobumons = [dobu_m1, dobu_m2, dobu_f1]

    view = BreedSelectView(user, dobumons, MagicMock())

    # モックのインタラクション
    interaction = MagicMock(spec=discord.Interaction)
    interaction.message.embeds = [discord.Embed()]
    interaction.response.edit_message = AsyncMock()

    # 1. 異性間交配 (M1 & F1)
    view.p1_id = "M1"
    view.p2_id = "F1"
    await view.update_message(interaction)

    args, kwargs = interaction.response.edit_message.call_args
    embed = kwargs["embed"]
    assert "血が禁忌に染まります" not in embed.description
    assert "👤 親1: **オス1 (♂)**" in embed.description
    assert "👤 親2: **メス1 (♀)**" in embed.description

    # 2. 同性間交配 (M1 & M2)
    view.p1_id = "M1"
    view.p2_id = "M2"
    await view.update_message(interaction)

    args, kwargs = interaction.response.edit_message.call_args
    embed = kwargs["embed"]
    assert "血が禁忌に染まります" in embed.description

    # 3. 同一固体
    view.p1_id = "M1"
    view.p2_id = "M1"
    await view.update_message(interaction)

    args, kwargs = interaction.response.edit_message.call_args
    embed = kwargs["embed"]
    assert "同じ個体同士は交配できません" in embed.description
