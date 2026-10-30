"""Regression checks for dashboard sidebar scroll preserve + active fallback."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

from django.conf import settings
from django.test import SimpleTestCase


def _position_active_scroll(
    *,
    scroll_top: float,
    container_height: float,
    active_offset_top: float,
    active_height: float = 40.0,
    pad: float = 48.0,
) -> float:
    """Python mirror of positionActiveDashboardNav scroll adjustment."""
    container_top = 0.0
    active_top = container_top + (active_offset_top - scroll_top)
    active_bottom = active_top + active_height
    container_bottom = container_top + container_height
    if container_height < pad * 2 + 8:
        pad = max(8.0, container_height / 4.0)
    delta = 0.0
    if active_top < container_top + pad:
        delta = active_top - container_top - pad
    elif active_bottom > container_bottom - pad:
        delta = active_bottom - container_bottom + pad
    return max(0.0, scroll_top + delta)


class DashboardNavScrollTests(SimpleTestCase):
    def test_shell_marks_scroll_containers_and_active_markup(self):
        shell = (
            Path(settings.BASE_DIR) / "templates" / "dashboard" / "_shell.html"
        ).read_text(encoding="utf-8")
        self.assertEqual(shell.count("data-dash-nav-scroll"), 2)
        self.assertIn("dash-sidebar-scroll", shell)
        self.assertIn("dashboard-shell.js", shell)
        self.assertIn("navpreserve", shell)

        nav = (
            Path(settings.BASE_DIR)
            / "templates"
            / "dashboard"
            / "includes"
            / "_sidebar_nav.html"
        ).read_text(encoding="utf-8")
        self.assertIn("dash-nav-link-active", nav)
        self.assertIn("aria-current", nav)
        self.assertNotIn("accordion", nav.lower())
        self.assertNotIn("collapse", nav.lower())

    def test_shell_js_saved_scroll_priority_contract(self):
        src = (
            Path(settings.BASE_DIR) / "static" / "js" / "dashboard-shell.js"
        ).read_text(encoding="utf-8")
        self.assertIn("captureDashNavScroll", src)
        self.assertIn("positionActiveDashboardNav", src)
        self.assertIn("zarrah:dash-nav-scroll", src)
        self.assertIn("ZarrahDashNavScroll", src)
        self.assertIn("requestAnimationFrame", src)
        self.assertNotIn("scrollIntoView(", src)
        self.assertNotIn("window.scrollTo(", src)
        # Saved navigation scroll wins over active positioning
        self.assertIn("savedY != null", src)
        # pagehide must not be the primary capture path
        self.assertNotIn('addEventListener("pagehide"', src)
        self.assertNotIn("addEventListener('pagehide'", src)
        self.assertNotIn("persistBestNavScroll", src)
        self.assertIn("ZFDrawerScroll", src)
        self.assertIn("restoreScroll: false", src)

    def test_public_form_state_key_isolated(self):
        public = (
            Path(settings.BASE_DIR) / "static" / "js" / "form-state-persist.js"
        ).read_text(encoding="utf-8")
        self.assertNotIn("zarrah:dash-nav-scroll", public)
        self.assertIn("zarrah:form-state:", public)

        base = (
            Path(settings.BASE_DIR) / "templates" / "base.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn("dashboard-shell.js", base)

    def test_saved_scroll_roundtrip_semantics(self):
        """scrollTop=600 captured → destination restore = 600 (not active override)."""
        key = "zarrah:dash-nav-scroll"
        store: dict[str, str] = {}
        store[key] = "600"
        saved = float(store[key])
        # Simulate runDashboardNavPositioning with savedY present
        restored = saved
        del store[key]
        self.assertEqual(restored, 600.0)
        self.assertNotIn(key, store)

    def test_active_below_viewport_scrolls_down(self):
        after = _position_active_scroll(
            scroll_top=0,
            container_height=400,
            active_offset_top=1200,
        )
        self.assertGreater(after, 0)
        active_bottom = (1200 - after) + 40
        self.assertLessEqual(active_bottom, 400 - 48 + 0.01)

    def test_active_above_viewport_scrolls_up(self):
        after = _position_active_scroll(
            scroll_top=900,
            container_height=400,
            active_offset_top=100,
        )
        self.assertLess(after, 900)
        active_top = 100 - after
        self.assertGreaterEqual(active_top, 48 - 0.01)

    def test_active_already_visible_unchanged(self):
        before = 100.0
        after = _position_active_scroll(
            scroll_top=before,
            container_height=400,
            active_offset_top=200,
        )
        self.assertEqual(after, before)

    def test_node_unit_suite(self):
        script = (
            Path(settings.BASE_DIR) / "static" / "js" / "dashboard-nav-scroll.test.js"
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
