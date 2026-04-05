import pytest
from textual.app import App
from textual.widgets import Input

from tests import FixtureData


@pytest.mark.asyncio
async def test_show_logs_page_reachable(tui_app: App, connected_data: FixtureData):
    from textual.widgets import Log

    async with tui_app.run_test() as pilot:
        tui_app.screen.query_one("#login-username-input", Input).value = "user1"
        tui_app.screen.query_one("#login-password-input", Input).value = "user1Password"
        await pilot.click("#login-submit-btn")
        await pilot.pause(0.05)

        await pilot.click("#sidebar-show-logs-btn")
        await pilot.pause(0.05)
        tui_app.screen.query_one("#show-logs-page")
        tui_app.screen.query_one("#tui-show-logs", Log)


@pytest.mark.asyncio
async def test_help_about_page_reachable(tui_app: App, connected_data: FixtureData):
    async with tui_app.run_test() as pilot:
        tui_app.screen.query_one("#login-username-input", Input).value = "user1"
        tui_app.screen.query_one("#login-password-input", Input).value = "user1Password"
        await pilot.click("#login-submit-btn")
        await pilot.pause(0.05)

        await pilot.click("#sidebar-help-about-btn")
        await pilot.pause(0.15)
        tui_app.screen.query_one("#help-about-page")
        tui_app.screen.query_one("#help-about-md")


@pytest.mark.asyncio
async def test_settings_page_reachable(tui_app: App, connected_data: FixtureData):
    async with tui_app.run_test() as pilot:
        tui_app.screen.query_one("#login-username-input", Input).value = "user2"
        tui_app.screen.query_one("#login-password-input", Input).value = "user2Password"
        await pilot.click("#login-submit-btn")
        await pilot.pause(0.05)

        await pilot.click("#sidebar-settings-btn")
        await pilot.pause(0.05)
        tui_app.screen.query_one("#settings-page")
