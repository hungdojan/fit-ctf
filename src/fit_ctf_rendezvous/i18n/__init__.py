"""UI strings and locale resources for FIT Rendezvous.

Locale resolution:

- **Before login:** ``FIT_RENDEZVOUS_LANG`` (``en`` or ``cs``) if set, otherwise English.
- **After login:** Values from that user's ``rendezvous_settings.json`` under the user
  share path (see ``user_rendezvous_settings``).
- **Logout:** In-memory locale resets so the login screen uses the pre-login rules again.

String tables live in ``strings_en.py`` and ``strings_cs.py``. Import ``i18n``
(the default ``RendezvousI18n`` instance) and use ``i18n.locale`` to read or set
the active locale; module-level ``tr()`` delegates to that instance.
"""

from __future__ import annotations

import os

from jinja2 import ChoiceLoader, FileSystemLoader

from fit_ctf_rendezvous.utils import get_resource_dir

from .strings_cs import STRINGS as STRINGS_CS
from .strings_en import STRINGS as STRINGS_EN


class RendezvousI18n:
    """Per-process locale state and lookups for Rendezvous UI strings."""

    def __init__(
        self,
        strings_by_locale: dict[str, dict[str, str]] | None = None,
        *,
        env_var: str = "FIT_RENDEZVOUS_LANG",
    ) -> None:
        self._table: dict[str, dict[str, str]] = strings_by_locale or {
            "en": STRINGS_EN,
            "cs": STRINGS_CS,
        }
        self._fallback = self._table.get("en", STRINGS_EN)
        self._env_var = env_var
        self._locale: str | None = None

    def _resolve_initial_locale(self) -> str:
        explicit = os.environ.get(self._env_var, "").strip().lower()
        if explicit in self._table:
            return explicit
        return "en"

    @property
    def locale(self) -> str:
        if self._locale is None:
            self._locale = self._resolve_initial_locale()
        return self._locale

    @locale.setter
    def locale(self, value: str) -> None:
        value = value.strip().lower()
        if value not in self._table:
            value = "en"
        self._locale = value

    def reset_locale_cache(self) -> None:
        """Clear in-memory locale (e.g. tests). Next read of ``locale`` resolves again."""
        self._locale = None

    def tr(self, key: str, **kwargs: str | int) -> str:
        """Translate a UI string; unknown keys fall back to English."""
        loc = self.locale
        s = self._table.get(loc, self._fallback).get(key)
        if s is None:
            s = self._fallback.get(key, key)
        return s.format(**kwargs) if kwargs else s

    def read_locale_markdown(self, filename: str) -> str:
        """Load ``filename`` from ``resources/<locale>/``, falling back to ``en``."""
        base = get_resource_dir()
        for lang in (self.locale, "en"):
            path = base / lang / filename
            if path.is_file():
                return path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Missing markdown resource {filename!r} under {base / 'en'}")

    def jinja_resources_loader(self) -> ChoiceLoader:
        """Prefer current locale under ``resources/``, then English."""
        base = get_resource_dir()
        return ChoiceLoader(
            [
                FileSystemLoader(base / self.locale),
                FileSystemLoader(base / "en"),
            ]
        )


i18n = RendezvousI18n()


def tr(key: str, **kwargs: str | int) -> str:
    return i18n.tr(key, **kwargs)


def reset_locale_cache() -> None:
    i18n.reset_locale_cache()


def read_locale_markdown(filename: str) -> str:
    return i18n.read_locale_markdown(filename)


def jinja_resources_loader() -> ChoiceLoader:
    return i18n.jinja_resources_loader()


__all__ = [
    "RendezvousI18n",
    "STRINGS_CS",
    "STRINGS_EN",
    "i18n",
    "jinja_resources_loader",
    "read_locale_markdown",
    "reset_locale_cache",
    "tr",
]
