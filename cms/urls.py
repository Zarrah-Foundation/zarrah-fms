from django.urls import path

from cms import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
]
