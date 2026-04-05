"""Czech UI strings for FIT Rendezvous."""

STRINGS: dict[str, str] = {
    # login
    "login.title": "Přihlášení do CTF",
    "login.username": "Uživatelské jméno",
    "login.password": "Heslo",
    "login.placeholder_username": "Uživatelské jméno",
    "login.placeholder_password": "Heslo",
    "login.show_password": "Zobrazit heslo",
    "login.quit": "Ukončit",
    "login.submit": "Přihlásit",
    # sidebar
    "sidebar.hello": "Ahoj, {username}",
    "sidebar.no_project": "Není vybrán projekt\nVyberte projekt níže",
    "sidebar.project_status_hint": "Zelená = běží · Žlutá = vypnuto",
    "sidebar.select_project": "Vybrat projekt",
    "sidebar.submit_secret": "Odeslat tajemství",
    "sidebar.project_info": "Informace o projektu",
    "sidebar.change_password": "Změnit heslo",
    "sidebar.upload_key": "Nahrát veřejný klíč",
    "sidebar.about_help": "Nápověda a O aplikaci",
    "sidebar.settings": "Nastavení",
    "sidebar.show_logs": "Zobrazit log",
    "sidebar.logout": "Odhlásit se",
    # show_logs
    "show_logs.border": "Log",
    "show_logs.intro": (
        "## Log\n\n"
        "Zprávy z backendu FIT CTF (loggery začínající na `fit_ctf…`) se zobrazují zde, "
        "když máte otevřenou tuto stránku. Seznam uchová nejvýše **2000** řádků. "
        "Výstup zároveň běžně pokračuje do souborů nebo na terminál."
    ),
    # welcome
    "welcome.border": "Vítejte",
    # project_info
    "project_info.border": "Informace o projektu",
    "project_info.tab_manage": "Správa instance",
    "project_info.tab_info": "Informace o projektu",
    "project_info.tab_leaderboard": "Žebříček",
    "project_info.start_stop_instance": "Spustit / zastavit instanci",
    "project_info.leaderboard_col_pos": "Poř.",
    "project_info.leaderboard_col_username": "Uživatel",
    "project_info.leaderboard_col_secrets": "Nalezená tajemství",
    "project_info.leaderboard_col_last_submit": "Čas posl. odeslání",
    "project_info.leaderboard_col_score": "Skóre",
    "project_info.select_project_prompt": (
        "# Projekt\n\nV postranní liště vyberte projekt, aby se zobrazil jeho popis."
    ),
    "project_info.no_description": "# {name}\n\n_Pro tento projekt není nastaven popis._",
    "project_info.ssh_error_supervisor": "**Došlo k chybě. Kontaktujte prosím cvičícího.**",
    "project_info.notify_booting": "Instance se spouští...",
    "project_info.notify_shutting_down": "Instance se vypíná...",
    "project_info.notify_operation_failed": "Operace selhala.",
    "project_info.notify_started": "Instance byla spuštěna.",
    "project_info.notify_shutdown": "Instance byla vypnuta...",
    # settings
    "settings.border": "Nastavení",
    "settings.heading": "## Nastavení",
    "settings.theme_hint": (
        "Uloží se pro uživatele v souboru rendezvous_settings.json ve složce uživatele."
    ),
    "settings.dark_theme": "Tmavý motiv",
    "settings.language": "Jazyk",
    "settings.language_hint": (
        "Projeví se ihned. Uloží se pro uživatele; před přihlášením platí "
        "FIT_RENDEZVOUS_LANG nebo angličtina."
    ),
    "settings.lang_en": "Angličtina",
    "settings.lang_cs": "Čeština",
    # submit_secret
    "submit_secret.border": "Odeslat tajemství",
    "submit_secret.secret_value": "Hodnota tajemství: ",
    "submit_secret.project": "Projekt: ",
    "submit_secret.placeholder_secret": "Tajemství",
    "submit_secret.validate": "Ověřit",
    "submit_secret.notify_no_project": "Není vybrán projekt.",
    "submit_secret.notify_success": "Tajemství bylo úspěšně odesláno",
    # upload_key
    "upload_key.border": "Nahrát klíč",
    "upload_key.public_key": "Veřejný klíč: ",
    "upload_key.placeholder": "Hodnota veřejného klíče",
    "upload_key.button": "Nahrát klíč",
    "upload_key.notify_success": "Klíč byl úspěšně nahrán",
    "upload_key.notify_fail": "Nahrání klíče selhalo: {error}",
    # selector
    "selector.border": "Vybrat projekt",
    "selector.deselect": "Zrušit výběr",
    # help_about
    "help_about.border": "Nápověda a O aplikaci",
    # change_password
    "change_password.border": "Změnit heslo",
    "change_password.old_password": "Staré heslo: ",
    "change_password.new_password": "Nové heslo: ",
    "change_password.new_password_again": "Nové heslo (znovu): ",
    "change_password.show": "zobrazit",
    "change_password.button": "Změnit heslo",
    "change_password.validator_incorrect": "Heslo není správné.",
    "change_password.validator_format": (
        "Neplatný formát – alespoň 8 znaků, jedno velké, jedno malé písmeno a číslice."
    ),
    "change_password.validator_mismatch": "Nová hesla se neshodují.",
    "change_password.notify_success": "Heslo bylo úspěšně změněno.",
    # app
    "app.cleanup": "Uklízím...",
    "app.cleanup_failed": "Úklid selhal.",
    "app.cleanup_done": "Hotovo!",
    # core
    "core.not_logged_in": "Uživatel není přihlášen!",
}
