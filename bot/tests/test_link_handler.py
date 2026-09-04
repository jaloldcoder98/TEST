"""/link after passwords (docs/DECISIONS.md D-10).

The command is kept but inert: it explains that the Telegram account *is* the account. These
tests exist mostly to make sure it never quietly grows a credential prompt again.
"""

import pytest

from handlers import link
from tests.conftest import make_message


@pytest.mark.asyncio
async def test_link_explains_that_the_account_is_already_connected(state, monkeypatch) -> None:
    monkeypatch.setattr(link.settings, "frontend_url", "", raising=False)
    message = make_message("/link")

    await link.link_command(message, state)

    assert message.calls, "/link said nothing"
    # The property that matters is behavioural, not lexical: the handler answers once and leaves
    # no FSM state behind, so it cannot be waiting for a credential. (Asserting on wording would
    # be wrong — the Uzbek copy legitimately says "no separate login and password needed".)
    assert len(message.calls) == 1
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_link_offers_the_mini_app_when_a_public_url_is_configured(state, monkeypatch) -> None:
    monkeypatch.setattr(link.settings, "frontend_url", "https://example.ngrok-free.app", raising=False)
    message = make_message("/link")

    await link.link_command(message, state)

    markup = message.calls[-1]["reply_markup"]
    assert markup is not None, "no Web App button offered"
    assert markup.inline_keyboard[0][0].web_app.url == "https://example.ngrok-free.app"


@pytest.mark.asyncio
async def test_link_clears_leftover_state(state) -> None:
    """/link doubles as an escape hatch: someone stuck mid-flow types it, so it must not leave
    them in a state that swallows their next message."""
    await state.set_state("SomeFlow:waiting")
    await link.link_command(make_message("/link"), state)
    assert await state.get_state() is None
