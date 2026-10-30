import io
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from accounts.models import Role
from members.forms import MemberApplicationForm
from members.models import (
    ApplicationDocumentRequest,
    ApplicationEvent,
    ApplicationStatus,
)
from members.services import (
    create_application_as_admin,
    find_application_for_status_lookup,
    issue_status_token,
    request_missing_documents,
    upload_requested_document,
)
from members.transitions import TransitionError, transition_application
from members.views import STATUS_SESSION_KEY

User = get_user_model()


def _admin_user(email="admin@example.com"):
    from django.utils import timezone

    user = User.objects.create_user(
        email=email,
        password="Str0ngPass!23",
        role=Role.SUPER_ADMIN,
    )
    user.email_verified = timezone.now()
    user.save(update_fields=["email_verified"])
    return user


def _png(name="photo.png"):
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), color=(20, 120, 80)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def _pdf(name="id.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 test", content_type="application/pdf")


def application_payload(**overrides):
    data = {
        "bangla_name": "মোহাম্মদ রহিম",
        "english_name": "Mohammad Rahim",
        "father_name": "আব্দুল করিম",
        "mother_name": "ফাতেমা বেগম",
        "gender": "MALE",
        "date_of_birth": date(1995, 5, 15),
        "marital_status": "SINGLE",
        "email": "rahim@example.com",
        "phone": "01712345678",
        "identity_type": "NID",
        "identity_number": "1234567890123",
        "present_division": "Dhaka",
        "present_district": "Dhaka",
        "present_upazila": "Dhanmondi",
        "present_union": "Ward 5",
        "present_address": "House 1, Road 2",
        "permanent_same_as_present": True,
        "is_expat": False,
        "is_student": False,
        "occupation": "Teacher",
        "education_type": "GENERAL",
        "education_level": "SECONDARY",
        "education_class": "CLASS_10",
        "education_status": "COMPLETED",
        "education_institution": "Dhaka Collegiate School",
        "education_passing_year": 2012,
        "education_result": "GPA 5.00",
    }
    data.update(overrides)
    return data


def make_application(**overrides):
    files = {
        "photo": _png(),
        "identity_document": _pdf(),
    }
    payload = application_payload(**overrides)
    form = MemberApplicationForm(data=payload, files=files)
    assert form.is_valid(), form.errors
    return form.save()


class TransitionTests(TestCase):
    def setUp(self):
        self.admin = _admin_user("admin@example.com")

    def test_pending_to_under_review_to_approved(self):
        app = make_application(email="a1@example.com", phone="01711111111")
        transition_application(app, ApplicationStatus.UNDER_REVIEW, self.admin)
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.UNDER_REVIEW)
        member = transition_application(app, ApplicationStatus.APPROVED, self.admin)
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.APPROVED)
        self.assertIsNotNone(member)
        self.assertTrue(
            app.events.filter(action=ApplicationEvent.Action.APPROVED).exists()
        )

    def test_under_review_to_rejected_to_under_review_to_approved(self):
        app = make_application(email="a2@example.com", phone="01722222222")
        transition_application(app, ApplicationStatus.UNDER_REVIEW, self.admin)
        transition_application(
            app, ApplicationStatus.REJECTED, self.admin, reason="Incomplete docs"
        )
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.REJECTED)
        transition_application(app, ApplicationStatus.UNDER_REVIEW, self.admin)
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.UNDER_REVIEW)
        transition_application(app, ApplicationStatus.APPROVED, self.admin)
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.APPROVED)
        actions = list(app.events.order_by("created_at").values_list("action", flat=True))
        self.assertIn(ApplicationEvent.Action.REJECTED, actions)
        self.assertIn(ApplicationEvent.Action.APPROVED, actions)

    def test_illegal_transition_from_approved(self):
        app = make_application(email="a3@example.com", phone="01733333333")
        transition_application(app, ApplicationStatus.APPROVED, self.admin)
        with self.assertRaises(TransitionError):
            transition_application(app, ApplicationStatus.UNDER_REVIEW, self.admin)


class AdminCreateFormTests(TestCase):
    def setUp(self):
        self.admin = _admin_user("admin2@example.com")

    def test_admin_create_rejects_underage(self):
        from members.forms import AdminMemberApplicationForm

        payload = application_payload(
            email="kid@example.com",
            phone="01744444444",
            date_of_birth=date.today() - timedelta(days=365 * 10),
        )
        form = AdminMemberApplicationForm(
            data={**payload, "auto_approve": False},
            files={"photo": _png(), "identity_document": _pdf()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("date_of_birth", form.errors)

    def test_admin_create_without_auto_approve_skips_member_account(self):
        from members.forms import AdminMemberApplicationForm

        payload = application_payload(email="pending@example.com", phone="01755555555")
        form = AdminMemberApplicationForm(
            data={**payload, "auto_approve": False},
            files={"photo": _png(), "identity_document": _pdf()},
        )
        self.assertTrue(form.is_valid(), form.errors)
        application, member = create_application_as_admin(
            form, creator=self.admin, auto_approve=False
        )
        self.assertIsNone(member)
        self.assertEqual(application.status, ApplicationStatus.PENDING)
        self.assertTrue(application.reference_code)
        self.assertTrue(
            application.events.filter(action=ApplicationEvent.Action.ADMIN_CREATED).exists()
        )


class StatusLookupAndDocumentsTests(TestCase):
    def setUp(self):
        self.admin = _admin_user("admin3@example.com")
        self.client = Client()

    def test_lookup_anti_enumeration_same_message(self):
        app = make_application(email="real@example.com", phone="01766666666")
        url = reverse("membership-status")
        with patch("members.views.send_status_lookup_email") as send_mock:
            r1 = self.client.post(
                url, {"reference_code": app.reference_code, "email": "real@example.com"}
            )
            r2 = self.client.post(
                url, {"reference_code": "ZFA-20990101-DEAD", "email": "nobody@example.com"}
            )
        self.assertEqual(r1.status_code, 302)
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(send_mock.call_count, 1)

    def test_status_requires_token_session(self):
        r = self.client.get(reverse("membership-status-view"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("membership-status"))

    def test_token_opens_status_and_e2e_missing_doc_flow(self):
        app = make_application(email="flow@example.com", phone="01777777777")
        transition_application(app, ApplicationStatus.UNDER_REVIEW, self.admin)
        docs = request_missing_documents(
            app,
            self.admin,
            [{"label": "Updated NID", "instruction": "Clear scan"}],
            admin_message="Please upload your NID again.",
        )
        self.assertEqual(len(docs), 1)
        self.assertTrue(
            app.events.filter(action=ApplicationEvent.Action.DOCUMENT_REQUESTED).exists()
        )

        token = issue_status_token(app)
        r = self.client.get(reverse("membership-status-token", kwargs={"token": token}))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("membership-status-view"))

        session = self.client.session
        self.assertEqual(session.get(STATUS_SESSION_KEY), str(app.pk))

        view = self.client.get(reverse("membership-status-view"))
        self.assertEqual(view.status_code, 200)
        self.assertContains(view, "Updated NID")
        self.assertContains(view, "Please upload your NID again.")

        # Cannot upload arbitrary / satisfied wrong request
        other = ApplicationDocumentRequest.objects.create(
            application=make_application(email="other@example.com", phone="01788888888"),
            document_label="Other",
            created_by=self.admin,
        )
        bad = self.client.post(
            reverse("membership-status-upload", kwargs={"request_id": other.pk}),
            {"uploaded_file": _pdf("hack.pdf")},
        )
        self.assertEqual(bad.status_code, 404)

        ok = self.client.post(
            reverse("membership-status-upload", kwargs={"request_id": docs[0].pk}),
            {"uploaded_file": _pdf("nid.pdf")},
        )
        self.assertEqual(ok.status_code, 302)
        docs[0].refresh_from_db()
        self.assertTrue(docs[0].is_satisfied)
        self.assertTrue(
            app.events.filter(action=ApplicationEvent.Action.DOCUMENT_UPLOADED).exists()
        )

        transition_application(app, ApplicationStatus.APPROVED, self.admin)
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.APPROVED)

        # Fresh token after approval so applicant can see Approved
        token2 = issue_status_token(app)
        self.client.get(reverse("membership-status-token", kwargs={"token": token2}))
        approved_view = self.client.get(reverse("membership-status-view"))
        self.assertContains(approved_view, "Approved")

    def test_find_application_requires_email_match(self):
        app = make_application(email="own@example.com", phone="01799999999")
        self.assertIsNone(
            find_application_for_status_lookup(app.reference_code, "wrong@example.com")
        )
        self.assertEqual(
            find_application_for_status_lookup(app.reference_code, "own@example.com").pk,
            app.pk,
        )

    def test_cannot_replace_unrelated_application_document_fields(self):
        app = make_application(email="doc@example.com", phone="01710101010")
        req = request_missing_documents(
            app, self.admin, [{"label": "Passport copy"}]
        )[0]
        upload_requested_document(req, _pdf("passport.pdf"))
        with self.assertRaises(ValueError):
            upload_requested_document(req, _pdf("again.pdf"))


class MembershipLandingTests(TestCase):
    def test_check_status_cta_present(self):
        from django.conf import settings

        self.client.post(reverse("set_language"), {"language": "en", "next": "/membership/"})
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        r = self.client.get(reverse("membership"))
        self.assertContains(r, reverse("membership-status"))
        self.assertContains(r, "Check Application Status")


class PublicApplyReferenceTests(TestCase):
    def test_public_apply_assigns_reference(self):
        app = make_application(email="pub@example.com", phone="01712121212")
        self.assertTrue(app.reference_code.startswith("ZFA-"))
        self.assertIsNotNone(app.reference_code)
