import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class NewsCategory(models.Model):
    """CMS-managed news/article category."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_bn = models.CharField(max_length=150)
    name_en = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, blank=True)
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name_en"]
        verbose_name_plural = "news categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name_en)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name_en


class News(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300, help_text="English title (primary).")
    title_bn = models.CharField(max_length=300, blank=True, default="")
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(
        NewsCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    excerpt = models.TextField(null=True, blank=True)
    excerpt_bn = models.TextField(blank=True, default="")
    content = models.TextField(help_text="English body (primary).")
    content_bn = models.TextField(blank=True, default="")
    featured_image = models.ImageField(upload_to="news/", null=True, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="news"
    )
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "news"

    @property
    def title_en(self):
        """Alias so ``bl:"title"`` works with the legacy ``title`` column."""
        return self.title

    @property
    def content_en(self):
        return self.content

    @property
    def excerpt_en(self):
        return self.excerpt or ""

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "article"
            candidate = base
            n = 2
            while News.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{n}"
                n += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
