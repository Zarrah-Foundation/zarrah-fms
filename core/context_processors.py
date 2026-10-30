from core.models import SiteSettings


def site_settings(request):
    """Expose the global branding singleton as ``{{ site_settings }}`` in
    every template (see templates/base.html, includes/nav.html,
    includes/footer.html). ``SiteSettings.load()`` is cached, so this adds
    no extra database query on most requests.
    """
    return {"site_settings": SiteSettings.load()}
