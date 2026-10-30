"""Regression checks for language-switch form/scroll persistence JS."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import unittest

from django.conf import settings
from django.test import SimpleTestCase


class _FakeSessionStorage:
    """Minimal sessionStorage stand-in for round-trip assertions."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def getItem(self, key: str):
        return self._store.get(key)

    def setItem(self, key: str, value: str) -> None:
        self._store[key] = str(value)

    def removeItem(self, key: str) -> None:
        self._store.pop(key, None)


def _storage_key(pathname: str) -> str:
    return f"zarrah:form-state:{pathname}"


def _capture_language_switch_scroll(
    storage: _FakeSessionStorage,
    *,
    pathname: str,
    scroll_x: float,
    scroll_y: float,
) -> None:
    """Python mirror of ZarrahFormState.capture scroll fields."""
    snapshot = {
        "fields": [],
        "activeField": None,
        "scrollX": scroll_x,
        "scrollY": scroll_y,
        "savedAt": 1,
    }
    storage.setItem(_storage_key(pathname), json.dumps(snapshot))


def _restore_language_switch_scroll(
    storage: _FakeSessionStorage,
    *,
    pathname: str,
) -> tuple[float | None, float | None]:
    """
    Python mirror of restore(): read snapshot, return scroll, clear storage.

    Mirrors the JS rule: no saved state → do nothing; after restore → clear.
    """
    raw = storage.getItem(_storage_key(pathname))
    if not raw:
        return None, None
    snapshot = json.loads(raw)
    scroll_x = snapshot.get("scrollX")
    scroll_y = snapshot.get("scrollY")
    storage.removeItem(_storage_key(pathname))
    if not isinstance(scroll_y, (int, float)):
        return None, None
    if not isinstance(scroll_x, (int, float)):
        scroll_x = 0
    return float(scroll_x), float(scroll_y)


class FormStatePersistJsTests(SimpleTestCase):
    def test_script_persists_and_restores_scroll_contract(self):
        src = (
            Path(settings.BASE_DIR) / "static" / "js" / "form-state-persist.js"
        ).read_text(encoding="utf-8")
        self.assertIn("scrollY", src)
        self.assertIn("scrollX", src)
        self.assertIn("data-language-switch", src)
        self.assertIn("requestAnimationFrame", src)
        self.assertIn("ZarrahFormState", src)
        # Must never force a global top jump.
        self.assertNotIn("scrollTo(0, 0)", src)
        self.assertNotIn("scrollTo(0,0)", src)

    def test_language_switch_markup_and_base_load(self):
        base = (
            Path(settings.BASE_DIR) / "templates" / "base.html"
        ).read_text(encoding="utf-8")
        switch = (
            Path(settings.BASE_DIR)
            / "templates"
            / "includes"
            / "_language_switch.html"
        ).read_text(encoding="utf-8")
        self.assertIn("form-state-persist.js", base)
        self.assertIn("langscroll", base)
        self.assertIn("data-language-switch", switch)
        self.assertIn('name="language"', switch)
        self.assertIn('type="submit"', switch)

    def test_scroll_middle_language_switch_restore_roundtrip(self):
        """
        scroll mid-page → language-switch capture → simulated redirect load
        → previous scroll restored and snapshot cleared.
        """
        storage = _FakeSessionStorage()
        pathname = "/about/"
        mid_y = 1200.0

        # No saved state → restore is a no-op.
        self.assertEqual(
            _restore_language_switch_scroll(storage, pathname=pathname),
            (None, None),
        )

        # User scrolled halfway, then submitted language switch.
        _capture_language_switch_scroll(
            storage, pathname=pathname, scroll_x=0, scroll_y=mid_y
        )
        raw = storage.getItem(_storage_key(pathname))
        self.assertIsNotNone(raw)
        payload = json.loads(raw)
        self.assertEqual(payload["scrollY"], mid_y)
        self.assertEqual(payload["scrollX"], 0)

        # Redirected page load starts at top, then restore runs.
        restored_x, restored_y = _restore_language_switch_scroll(
            storage, pathname=pathname
        )
        self.assertEqual(restored_x, 0.0)
        self.assertEqual(restored_y, mid_y)
        self.assertIsNone(storage.getItem(_storage_key(pathname)))

        # Ordinary navigation / second load has nothing left to restore.
        self.assertEqual(
            _restore_language_switch_scroll(storage, pathname=pathname),
            (None, None),
        )

    def test_node_unit_suite_scroll_restore(self):
        script = (
            Path(settings.BASE_DIR) / "static" / "js" / "form-state-persist.test.js"
        )
        try:
            result = subprocess.run(
                ["node", str(script)],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(settings.BASE_DIR),
            )
        except FileNotFoundError:
            raise unittest.SkipTest("node not available")
        self.assertEqual(
            result.returncode,
            0,
            msg=result.stdout + "\n" + result.stderr,
        )
        self.assertIn("OK", result.stdout)
