from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from core.email import send_email


class ContactForm(forms.Form):
    name = forms.CharField(label=_("Name"), max_length=200, widget=forms.TextInput(attrs={"class": "form-input"}))
    email = forms.EmailField(label=_("Email"), widget=forms.EmailInput(attrs={"class": "form-input"}))
    subject = forms.CharField(label=_("Subject"), max_length=300, widget=forms.TextInput(attrs={"class": "form-input"}))
    message = forms.CharField(label=_("Message"), widget=forms.Textarea(attrs={"rows": 5, "class": "form-input"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.templatetags.i18n_extras import apply_zf_form_labels

        apply_zf_form_labels(
            self,
            {
                "name": "Name",
                "email": "Email",
                "subject": "Subject",
                "message": "Message",
            },
        )

    def send_email(self):
        data = self.cleaned_data
        send_email(
            subject=f"[Contact] {data['subject']}",
            message=f"From: {data['name']} <{data['email']}>\n\n{data['message']}",
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
        )


class VolunteerForm(forms.Form):
    name = forms.CharField(label=_("Name"), max_length=200, widget=forms.TextInput(attrs={"class": "form-input"}))
    email = forms.EmailField(label=_("Email"), widget=forms.EmailInput(attrs={"class": "form-input"}))
    phone = forms.CharField(label=_("Phone"), max_length=20, widget=forms.TextInput(attrs={"class": "form-input"}))
    message = forms.CharField(label=_("Message"), widget=forms.Textarea(attrs={"rows": 5, "class": "form-input"}))

    def send_email(self):
        data = self.cleaned_data
        send_email(
            subject=f"[Volunteer] {data['name']}",
            message=(
                f"Name: {data['name']}\nEmail: {data['email']}\nPhone: {data['phone']}\n\n"
                f"{data['message']}"
            ),
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
        )
