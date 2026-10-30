from django.urls import path

from news import views

urlpatterns = [
    path("news/", views.NewsListView.as_view(), name="news"),
    path("news/<slug:slug>/", views.NewsDetailView.as_view(), name="news-detail"),
]
