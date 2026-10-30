from django.urls import path

from foundation_api.views.foundation import FoundationAPIView

app_name = "foundation_api"

urlpatterns = [
    path(
        "v1/public/foundation/",
        FoundationAPIView.as_view(),
        name="foundation",
    ),
]