from textual.app import App
from textual.widgets import Label

from fit_ctf_models.utils.sessions import LoginSession
from tests import FixtureData


async def test_login(tui_app: App, connected_data: FixtureData):
    ctf_app, _ = connected_data
    async with tui_app.run_test() as pilot:
        await pilot.click("#login-username-input")
        await pilot.press(*"user1")

        await pilot.click("#login-password-input")
        await pilot.press(*"wrongPassword")

        await pilot.click("#login-submit-btn")
        assert (
            tui_app.screen.query_one("#login-message-label", Label).styles.visibility
            == "visible"
        )
        await pilot.press("user1Password")
        user = ctf_app.user_mgr.get_user("user1")
        assert user and not user.sessions

        await pilot.click("#login-submit-btn")
        user = ctf_app.user_mgr.get_user("user1")
        assert (
            user
            and user.sessions
            and user.sessions[-1].state == LoginSession.State.LOGIN
        )
