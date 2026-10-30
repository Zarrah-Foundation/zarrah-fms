"""Regression checks for mobile drawer scroll-lock JS."""

from pathlib import Path
from urllib.parse import urljoin, urlparse
import subprocess
import unittest

from django.conf import settings
from django.test import SimpleTestCase


def _is_leaving_document(href: str, current: str) -> bool:
    """Python mirror of ZFDrawerScroll.isLeavingDocument for regression."""
    if href is None or href == "" or href.startswith("#"):
        return False
    if href.lower().startswith("javascript:"):
        return False
    try:
        resolved = urljoin(current, href)
        url = urlparse(resolved)
        cur = urlparse(current)
        if url.scheme and cur.scheme and (url.scheme, url.netloc) != (cur.scheme, cur.netloc):
            return True
        if url.path != cur.path or url.query != cur.query:
            return True
        return False
    except Exception:
        return True


class DrawerScrollLockJsTests(SimpleTestCase):
    def test_helper_and_consumers_ship_expected_contracts(self):
        base = Path(settings.BASE_DIR) / "static" / "js"
        helper = (base / "drawer-scroll-lock.js").read_text(encoding="utf-8")
        public = (base / "nav-drawer.js").read_text(encoding="utf-8")
        dash = (base / "dashboard-shell.js").read_text(encoding="utf-8")

        self.assertIn("ZFDrawerScroll", helper)
        self.assertIn("preventScroll", helper)
        self.assertIn("lockBodyScroll", helper)
        self.assertIn("unlockBodyScroll", helper)
        self.assertIn("isLeavingDocument", helper)
        # Must restore saved Y — never a blanket top jump helper.
        self.assertNotIn("scrollTo(0, 0)", helper)
        self.assertNotIn("scrollTo(0,0)", helper)

        self.assertIn("ZFDrawerScroll", public)
        self.assertIn("restoreScroll: false", public)
        self.assertIn("isLeavingDocument", public)

        self.assertIn("ZFDrawerScroll", dash)
        self.assertIn("restoreScroll: false", dash)

    def test_templates_load_helper_before_drawers(self):
        base = Path(settings.BASE_DIR) / "templates"
        public = (base / "base.html").read_text(encoding="utf-8")
        dash = (base / "dashboard" / "_shell.html").read_text(encoding="utf-8")
        self.assertIn("drawer-scroll-lock.js", public)
        self.assertLess(
            public.index("drawer-scroll-lock.js"),
            public.index("nav-drawer.js"),
        )
        self.assertIn("drawer-scroll-lock.js", dash)
        self.assertLess(
            dash.index("drawer-scroll-lock.js"),
            dash.index("dashboard-shell.js"),
        )

    def test_is_leaving_document_logic(self):
        current = "https://example.com/about/"
        self.assertFalse(_is_leaving_document("#section", current))
        self.assertFalse(_is_leaving_document("", current))
        self.assertFalse(_is_leaving_document("/about/", current))
        self.assertFalse(_is_leaving_document("/about/#team", current))
        self.assertTrue(_is_leaving_document("/contact/", current))
        self.assertTrue(_is_leaving_document("https://other.example/", current))

    def test_css_lock_class_present(self):
        css = (
            Path(settings.BASE_DIR) / "static" / "css" / "components.css"
        ).read_text(encoding="utf-8")
        self.assertIn(".drawer-lock-scroll", css)

    def test_node_unit_suite(self):
        script = Path(settings.BASE_DIR) / "static" / "js" / "drawer-scroll-lock.test.js"
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
