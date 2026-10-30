"""Template-only helpers for dressing up Django forms.

These tags let a template override a bound field's display ``label`` and
add a ``placeholder`` without editing the Form/Model classes that define
it. Nothing here touches validation, cleaning, or any other business
logic — both tags only mutate presentation state on the current request's
form instance.

``set_label`` deliberately mutates the ``BoundField.label`` attribute
itself rather than the underlying ``Field.label``: Django's
``BoundField.__init__`` copies ``field.label`` into ``self.label`` as a
plain string *once*, at construction time, so mutating the ``Field``
afterwards has no effect on a ``BoundField`` that already exists.
``Form.__getitem__`` also caches one ``BoundField`` per name on the form
instance (``_bound_fields_cache``), so every later read of
``form.<name>`` in the *same* render — the per-field partial, an error
summary loop, etc. — resolves to that same cached object and sees the
overridden label. This means the label only needs to be declared once per
field per page, as early as possible (before anything else reads it).
"""

from django import template

register = template.Library()


@register.simple_tag
def set_label(field, text):
    """Usage: {% set_label form.bangla_name "Name (in Bangla)" %}"""
    if text:
        field.label = text
    return ""


@register.simple_tag
def set_placeholder(field, text):
    """Usage: {% set_placeholder form.email "e.g. karim@example.com" %}"""
    if text:
        field.field.widget.attrs["placeholder"] = text
    return ""
