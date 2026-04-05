"""Per-user Rendezvous UI preferences (JSON under the central user share directory)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from fit_ctf.path_mgmt import PathManagement
from fit_ctf_models.user import User

SETTINGS_FILENAME = "rendezvous_settings.json"
SCHEMA_VERSION = 1
_VALID_LOCALES = frozenset({"en", "cs"})
LocaleCode = Literal["en", "cs"]


class RendezvousUserSettingsDict(TypedDict):
    """Shape of ``rendezvous_settings.json`` on disk."""

    schema_version: int
    locale: str
    dark_theme: bool


@dataclass(frozen=True, slots=True)
class RendezvousUserSettings:
    """Validated UI preferences for one Rendezvous user."""

    schema_version: int
    locale: LocaleCode
    dark_theme: bool

    @classmethod
    def defaults(cls) -> RendezvousUserSettings:
        return cls(
            schema_version=SCHEMA_VERSION,
            locale="en",
            dark_theme=True,
        )

    @classmethod
    def create(cls, *, locale: str, dark_theme: bool) -> RendezvousUserSettings:
        loc = locale.strip().lower()
        code: LocaleCode = loc if loc in _VALID_LOCALES else "en"
        return cls(
            schema_version=SCHEMA_VERSION,
            locale=code,
            dark_theme=bool(dark_theme),
        )

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> RendezvousUserSettings:
        """Build from parsed JSON or other mapping; invalid fields fall back to defaults."""
        base = cls.defaults()
        if not isinstance(raw, Mapping):
            return base
        loc = raw.get("locale", base.locale)
        locale: LocaleCode = base.locale
        if isinstance(loc, str) and loc.strip().lower() in _VALID_LOCALES:
            locale = cast(LocaleCode, loc.strip().lower())
        dt = raw.get("dark_theme", base.dark_theme)
        dark = bool(dt) if isinstance(dt, bool) else base.dark_theme
        sv = raw.get("schema_version", base.schema_version)
        schema = int(sv) if isinstance(sv, int) else base.schema_version
        return cls(schema_version=schema, locale=locale, dark_theme=dark)

    def to_json_dict(self) -> RendezvousUserSettingsDict:
        return {
            "schema_version": self.schema_version,
            "locale": self.locale,
            "dark_theme": self.dark_theme,
        }


def _settings_path(paths: PathManagement, user: User) -> Path:
    return paths.user_path(user) / SETTINGS_FILENAME


def load(paths: PathManagement, user: User) -> RendezvousUserSettings:
    """Return merged settings; missing or invalid files yield ``defaults()``."""
    path = _settings_path(paths, user)
    if not path.is_file():
        return RendezvousUserSettings.defaults()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return RendezvousUserSettings.defaults()
    if not isinstance(raw, dict):
        return RendezvousUserSettings.defaults()
    return RendezvousUserSettings.from_mapping(raw)


def save(paths: PathManagement, user: User, settings: RendezvousUserSettings) -> None:
    """Write ``rendezvous_settings.json`` for ``user`` (creates parent dirs)."""
    path = _settings_path(paths, user)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings.to_json_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


def apply_to_app(app: Any, settings: RendezvousUserSettings) -> None:
    """Apply settings to ``RendezvousApp`` (theme + ``i18n.locale``)."""
    from fit_ctf_rendezvous.i18n import i18n

    i18n.locale = settings.locale
    app.theme = "textual-dark" if settings.dark_theme else "textual-light"


def default_settings() -> RendezvousUserSettings:
    """Same as ``RendezvousUserSettings.defaults()`` (stable name for callers/tests)."""
    return RendezvousUserSettings.defaults()


__all__ = [
    "LocaleCode",
    "RendezvousUserSettings",
    "RendezvousUserSettingsDict",
    "SETTINGS_FILENAME",
    "apply_to_app",
    "default_settings",
    "load",
    "save",
]
