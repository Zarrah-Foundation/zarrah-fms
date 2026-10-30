from django.urls import path

from finance import views

urlpatterns = [
    path("transparency/", views.TransparencyView.as_view(), name="transparency"),
]
