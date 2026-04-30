from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from core.ui.view_base import BaseView, ErrorHandlerMixin
from core.utils.exceptions import BotError


class CustomDummyError(BotError):
    pass


class DummyView(BaseView):
    pass


def dummy_formatter(msg: str) -> discord.Embed:
    return discord.Embed(title="Dummy Formatting", description=msg)


@pytest.mark.asyncio
async def test_error_handler_mixin_registers_formatter():
    # Register formatter
    ErrorHandlerMixin.register_error_formatter(CustomDummyError, dummy_formatter)

    view = DummyView()
    interaction = MagicMock(spec=discord.Interaction)

    # Setup response: unhandled response (should use send_message)
    interaction.response = MagicMock()
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()

    error = CustomDummyError("This is a dummy test limit")

    # Process error
    await view.on_error(interaction, error, None)

    interaction.response.send_message.assert_called_once()
    _, kwargs = interaction.response.send_message.call_args
    assert "embed" in kwargs
    embed = kwargs["embed"]
    assert embed.title == "Dummy Formatting"
    assert embed.description == "This is a dummy test limit"
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_error_handler_mixin_followup():
    ErrorHandlerMixin.register_error_formatter(CustomDummyError, dummy_formatter)

    view = DummyView()
    interaction = MagicMock(spec=discord.Interaction)

    # Setup response: Already responded (should use followup.send)
    interaction.response = MagicMock()
    interaction.response.is_done.return_value = True

    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    error = CustomDummyError("Another dummy error")

    await view.on_error(interaction, error, None)

    interaction.followup.send.assert_called_once()
    _, kwargs = interaction.followup.send.call_args
    embed = kwargs["embed"]
    assert embed.title == "Dummy Formatting"
    assert embed.description == "Another dummy error"
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_unknown_interaction_ignore():
    from discord.errors import NotFound

    view = DummyView()
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()

    # Mock Discord's NotFound with code 10062
    error = NotFound(response=MagicMock(), message="Unknown interaction")
    error.code = 10062

    await view.on_error(interaction, error, None)

    # Should be entirely ignored without sending anything
    interaction.response.send_message.assert_not_called()
    interaction.followup.send.assert_not_called()
