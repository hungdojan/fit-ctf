import os

import pytest
from textual.app import App
from textual.widgets import Input, Label

from fit_ctf.models.utils.sessions import LoginSession
from fit_ctf_rendezvous.screens.app_screen.app_screen import AppScreen
from tests import FixtureData

if os.getenv("ENABLE_RENDEZVOUS_TESTING", "0") == "0":
    pytest.skip("Rendezvous TUI app testing not enabled", allow_module_level=True)


@pytest.mark.skip()
@pytest.mark.asyncio
async def test_login(tui_app: App, connected_data: FixtureData):
    ctf_app, _ = connected_data
    async with tui_app.run_test() as pilot:
        tui_app.screen.query_one("#login-password-input", Input).value = "wrongPassword"
        tui_app.screen.query_one("#login-username-input", Input).value = "user1"

        await pilot.click("#login-submit-btn")
        await pilot.pause(0.05)
        assert (
            tui_app.screen.query_one("#login-message-label", Label).styles.visibility
            == "visible"
        )

        tui_app.screen.query_one("#login-password-input", Input).value = "user1Password"
        user = ctf_app.user_mgr.get_user("user1")
        assert user is not None

        await pilot.click("#login-submit-btn")
        await pilot.pause(0.1)
        user = ctf_app.user_mgr.get_user("user1")
        assert (
            user
            and user.sessions
            and user.sessions[-1].state == LoginSession.State.LOGIN
        )
        assert isinstance(tui_app.screen, AppScreen)


@pytest.mark.asyncio
async def test_sidebar_opens_project_selector(
    tui_app: App, connected_data: FixtureData
):
    async with tui_app.run_test() as pilot:
        tui_app.screen.query_one("#login-username-input", Input).value = "user1"
        tui_app.screen.query_one("#login-password-input", Input).value = "user1Password"
        await pilot.click("#login-submit-btn")
        await pilot.pause(0.05)

        assert isinstance(tui_app.screen, AppScreen)
        await pilot.click("#sidebar-select-project-btn")
        await pilot.pause(0.05)
        tui_app.screen.query_one("#project-selector")
