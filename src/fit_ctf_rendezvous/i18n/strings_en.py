"""English UI strings for FIT Rendezvous."""

STRINGS: dict[str, str] = {
    # login
    "login.title": "CTF Login",
    "login.username": "Username",
    "login.password": "Password",
    "login.placeholder_username": "Username",
    "login.placeholder_password": "Password",
    "login.show_password": "Show Password",
    "login.quit": "Quit",
    "login.submit": "Submit",
    # sidebar
    "sidebar.hello": "Hello, {username}",
    "sidebar.no_project": "No project selected\nSelect a project below",
    "sidebar.project_status_hint": "Green = running · Yellow = idle",
    "sidebar.select_project": "Select Project",
    "sidebar.submit_secret": "Submit Secret",
    "sidebar.project_info": "Project Info",
    "sidebar.change_password": "Change Password",
    "sidebar.upload_key": "Upload public key",
    "sidebar.about_help": "About & Help",
    "sidebar.settings": "Settings",
    "sidebar.show_logs": "Show logs",
    "sidebar.logout": "Logout",
    # show_logs
    "show_logs.border": "Logs",
    "show_logs.intro": (
        "## Logs\n\n"
        "Messages from FIT CTF backends (loggers named `fit_ctf…`) appear here while "
        "this page is open. The list keeps at most the last **2000** lines. "
        "The same output still goes to log files or the terminal as usual."
    ),
    # welcome
    "welcome.border": "Welcome",
    # project_info
    "project_info.border": "Project Info",
    "project_info.tab_manage": "Manage instance",
    "project_info.tab_info": "Project Info",
    "project_info.tab_leaderboard": "Leaderboard",
    "project_info.start_stop_instance": "Start/Stop Instance",
    "project_info.leaderboard_col_pos": "Pos",
    "project_info.leaderboard_col_username": "Username",
    "project_info.leaderboard_col_secrets": "Found Secrets",
    "project_info.leaderboard_col_last_submit": "Last Submit Time",
    "project_info.leaderboard_col_score": "Score",
    "project_info.select_project_prompt": (
        "# Project\n\nSelect a project in the sidebar to see its description."
    ),
    "project_info.no_description": "# {name}\n\n_No description configured for this project._",
    "project_info.ssh_error_supervisor": "**Error occurred. Please contact the supervisor.**",
    "project_info.notify_booting": "Instance is booting...",
    "project_info.notify_shutting_down": "Instance is shutting down...",
    "project_info.notify_operation_failed": "Operation failed.",
    "project_info.notify_started": "Instance has started.",
    "project_info.notify_shutdown": "Instance has shut down...",
    # settings
    "settings.border": "Settings",
    "settings.heading": "## Settings",
    "settings.theme_hint": "Saved per user in rendezvous_settings.json under your user folder.",
    "settings.dark_theme": "Dark theme",
    "settings.language": "Language",
    "settings.language_hint": (
        "Applies immediately. Saved per user; before login, FIT_RENDEZVOUS_LANG or English is used."
    ),
    "settings.lang_en": "English",
    "settings.lang_cs": "Czech (Čeština)",
    # submit_secret
    "submit_secret.border": "Submit Secret",
    "submit_secret.secret_value": "Secret value: ",
    "submit_secret.project": "Project: ",
    "submit_secret.placeholder_secret": "Secret",
    "submit_secret.validate": "Validate",
    "submit_secret.notify_no_project": "Project not selected.",
    "submit_secret.notify_success": "Secret successfully submitted",
    # upload_key
    "upload_key.border": "Upload Key",
    "upload_key.public_key": "Public key: ",
    "upload_key.placeholder": "Public key value",
    "upload_key.button": "Upload Key",
    "upload_key.notify_success": "Key successfully uploaded",
    "upload_key.notify_fail": "Uploading key failed: {error}",
    # selector
    "selector.border": "Select Project",
    "selector.deselect": "Deselect",
    # help_about
    "help_about.border": "About & Help",
    # change_password
    "change_password.border": "Change Password",
    "change_password.old_password": "Old password: ",
    "change_password.new_password": "New Password: ",
    "change_password.new_password_again": "New Password (again): ",
    "change_password.show": "show",
    "change_password.button": "Change password",
    "change_password.validator_incorrect": "Password is incorrect.",
    "change_password.validator_format": (
        "Invalid format, requires at least 8 characters, one upper, one lower "
        "character and a digit."
    ),
    "change_password.validator_mismatch": "New passwords do not match.",
    "change_password.notify_success": "Password changed successfully.",
    # app
    "app.cleanup": "Cleaning Up...",
    "app.cleanup_failed": "Cleanup failed.",
    "app.cleanup_done": "Cleanup done!",
    # core
    "core.not_logged_in": "User not logged in!",
}
