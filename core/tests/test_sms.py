"""Tests for provider-agnostic SMS settings and verification service."""

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from core.models import SmsSettings
from core.sms.console import ConsoleSmsProvider
from core.sms.http_generic import HttpGenericSmsProvider
from core.sms.service import SMSService, _code_key


class SmsSettingsModelTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_singleton_load_and_save(self):
        a = SmsSettings.load()
        b = SmsSettings.load()
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(a.pk, SmsSettings.SINGLETON_ID)

        a.enabled = True
        a.provider = SmsSettings.Provider.HTTP_GENERIC
        a.api_url = "https://sms.example/send"
        a.api_key = "secret-key"
        a.save()

        cache.clear()
        reloaded = SmsSettings.load()
        self.assertTrue(reloaded.enabled)
        self.assertEqual(reloaded.provider, SmsSettings.Provider.HTTP_GENERIC)
        self.assertEqual(reloaded.api_key, "secret-key")

    def test_delete_is_noop(self):
        obj = SmsSettings.load()
        pk = obj.pk
        self.assertTrue(SmsSettings.objects.filter(pk=pk).exists())
        obj.delete()
        self.assertTrue(SmsSettings.objects.filter(pk=pk).exists())


class SMSServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.cfg = SmsSettings.load()
        self.cfg.enabled = True
        self.cfg.provider = SmsSettings.Provider.CONSOLE
        self.cfg.verification_timeout_seconds = 300
        self.cfg.resend_cooldown_seconds = 60
        self.cfg.max_attempts = 5
        self.cfg.max_sends_per_hour = 5
        self.cfg.save()

    @override_settings(DEBUG=True)
    def test_debug_console_provider(self):
        provider = SMSService.get_provider()
        self.assertIsInstance(provider, ConsoleSmsProvider)

    @override_settings(DEBUG=False)
    def test_http_provider_when_enabled(self):
        self.cfg.provider = SmsSettings.Provider.HTTP_GENERIC
        self.cfg.api_url = "https://sms.example/send"
        self.cfg.api_key = "k"
        self.cfg.save()
        cache.clear()
        provider = SMSService.get_provider()
        self.assertIsInstance(provider, HttpGenericSmsProvider)

    @override_settings(DEBUG=True)
    def test_send_and_verify_code(self):
        ok, msg = SMSService.send_verification_code("+8801712345678")
        self.assertTrue(ok)
        stored = cache.get(_code_key("+8801712345678"))
        self.assertIsNotNone(stored)
        self.assertEqual(len(stored), 6)

        bad, _ = SMSService.verify_code("+8801712345678", "000000")
        self.assertFalse(bad)

        good, _ = SMSService.verify_code("+8801712345678", stored)
        self.assertTrue(good)
        self.assertIsNone(cache.get(_code_key("+8801712345678")))

    @override_settings(DEBUG=True)
    def test_max_attempts(self):
        SMSService.send_verification_code("01711111111")
        for _ in range(5):
            ok, _ = SMSService.verify_code("01711111111", "000000")
            self.assertFalse(ok)
        ok, msg = SMSService.verify_code("01711111111", "000000")
        self.assertFalse(ok)
        self.assertIn("Too many", msg)

    @override_settings(DEBUG=True)
    def test_resend_cooldown(self):
        ok1, _ = SMSService.send_verification_code("01722222222")
        self.assertTrue(ok1)
        ok2, msg = SMSService.send_verification_code("01722222222")
        self.assertFalse(ok2)
        self.assertIn("wait", msg.lower())

    @override_settings(DEBUG=False)
    @patch("core.sms.http_generic.requests.post")
    def test_http_generic_posts_without_leaking_in_return(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "ok"
        self.cfg.provider = SmsSettings.Provider.HTTP_GENERIC
        self.cfg.api_url = "https://sms.example/send"
        self.cfg.api_key = "super-secret"
        self.cfg.sender_id = "ZARRAH"
        self.cfg.save()
        cache.clear()

        ok = SMSService.send_sms("01700000000", "Hello")
        self.assertTrue(ok)
        mock_post.assert_called_once()
        kwargs = mock_post.call_args.kwargs
        self.assertEqual(kwargs["json"]["to"], "01700000000")
        # Secret is only in headers, not returned by send_sms
        self.assertIn("Authorization", kwargs["headers"])
