from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView

from core.maps import resolve_maps_embed_url
from pages import about_data, constitution_data, privacy_data, terms_data
from pages.forms import ContactForm, VolunteerForm


class AboutView(TemplateView):
    template_name = "pages/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(about_data.get_context())
        return context


class ObjectivesView(TemplateView):
    template_name = "pages/objectives.html"

    def get_context_data(self, **kwargs):
        from pages.organization_data import (
            AREAS_OF_WORK,
            OBJECTIVES,
            OBJECTIVES_PAGE,
            categorized_objectives,
        )

        context = super().get_context_data(**kwargs)
        context["objectives"] = OBJECTIVES
        context["objectives_page"] = OBJECTIVES_PAGE
        context["objective_areas"] = AREAS_OF_WORK
        context["objective_categories"] = categorized_objectives()
        return context


class ConstitutionView(TemplateView):
    template_name = "pages/constitution.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(constitution_data.get_context())
        return context


class FAQView(TemplateView):
    template_name = "pages/faq.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from community.models import FAQ

        context["faqs"] = FAQ.objects.filter(is_active=True).order_by("display_order")
        return context


class PrivacyView(TemplateView):
    template_name = "pages/privacy.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(privacy_data.get_context())
        return context


class TermsView(TemplateView):
    template_name = "pages/terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(terms_data.get_context())
        return context


class ContactView(FormView):
    template_name = "pages/contact.html"
    form_class = ContactForm
    success_url = "/contact/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.models import SiteSettings
        from django.utils.translation import get_language

        settings = SiteSettings.load()
        context["maps_embed_url"] = resolve_maps_embed_url(settings)
        from pages.organization_data import PRINCIPAL_OFFICE_BN, PRINCIPAL_OFFICE_EN

        context["contact_office_en"] = (settings.address_en or "").strip() or PRINCIPAL_OFFICE_EN
        context["contact_office_bn"] = (settings.address_bn or "").strip() or PRINCIPAL_OFFICE_BN
        lang_bn = (get_language() or "").startswith("bn")
        office = (settings.localized_address() or "").strip()
        if not office:
            office = PRINCIPAL_OFFICE_BN if lang_bn else PRINCIPAL_OFFICE_EN
        context["contact_office"] = office
        context["contact_office_lang"] = "bn" if lang_bn else "en"
        return context

    def form_valid(self, form):
        form.send_email()
        data = form.cleaned_data
        try:
            from community.models import ContactMessage

            msg = ContactMessage.objects.create(
                name=data["name"], email=data["email"],
                subject=data["subject"], message=data["message"],
            )
            from audit.notifications import ADMIN_ROLES, NotificationType, notify_roles

            notify_roles(
                ADMIN_ROLES,
                title="New contact message",
                message=f"{data['name']}: {data['subject']}",
                ntype=NotificationType.NEW_CONTACT_MESSAGE,
                related_object=msg,
            )
        except Exception:
            pass
        from core.templatetags.i18n_extras import zf_text

        messages.success(
            self.request,
            zf_text("Your message has been sent. We will get back to you soon."),
        )
        return super().form_valid(form)


class VolunteerView(FormView):
    template_name = "pages/volunteer.html"
    form_class = VolunteerForm
    success_url = "/volunteer/"

    def form_valid(self, form):
        form.send_email()
        data = form.cleaned_data
        try:
            from community.models import Volunteer

            vol = Volunteer.objects.create(
                name=data["name"], email=data["email"],
                phone=data["phone"], message=data.get("message", ""),
            )
            from audit.notifications import ADMIN_ROLES, NotificationType, notify_roles

            notify_roles(
                ADMIN_ROLES,
                title="New volunteer registration",
                message=f"{data['name']} ({data['phone']}) registered to volunteer.",
                ntype=NotificationType.VOLUNTEER_REGISTRATION,
                related_object=vol,
            )
        except Exception:
            pass
        messages.success(self.request, _("Thank you for your interest in volunteering!"))
        return super().form_valid(form)
