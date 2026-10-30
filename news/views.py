from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView

from news.models import News


class NewsListView(ListView):
    model = News
    template_name = "news/list.html"
    context_object_name = "news_list"
    paginate_by = 12

    def get_queryset(self):
        return News.objects.filter(is_published=True).order_by("-published_at", "-created_at")


class NewsDetailView(DetailView):
    model = News
    template_name = "news/detail.html"
    context_object_name = "article"
    slug_url_kwarg = "slug"

    def get_object(self):
        article = get_object_or_404(News, slug=self.kwargs["slug"], is_published=True)
        News.objects.filter(pk=article.pk).update(view_count=F("view_count") + 1)
        article.refresh_from_db()
        return article
