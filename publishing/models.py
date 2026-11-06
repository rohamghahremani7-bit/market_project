import os
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
def validate_article_image(image):
    ext = os.path.splitext(image.name)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        raise ValidationError('فرمت تصویر باید JPG، PNG یا WebP باشد.')
    if image.size > settings.ARTICLE_IMAGE_MAX_MB * 1024 * 1024:
        raise ValidationError(f'حجم تصویر نباید بیشتر از {settings.ARTICLE_IMAGE_MAX_MB} مگابایت باشد.')

class Article(models.Model):
    class Direction(models.TextChoices):
        BULLISH = 'BULLISH', 'صعودی'
        BEARISH = 'BEARISH', 'نزولی'
        NEUTRAL = 'NEUTRAL', 'خنثی'
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'پیش‌نویس'
        PENDING = 'PENDING', 'در انتظار تأیید'
        PUBLISHED = 'PUBLISHED', 'منتشرشده'
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=250, unique=True, allow_unicode=True, blank=True)
    excerpt = models.CharField(max_length=360, blank=True)
    body = models.TextField()
    image = models.ImageField(upload_to='articles/%Y/%m/', blank=True, null=True, validators=[validate_article_image])
    symbol = models.ForeignKey('marketdata.Symbol', on_delete=models.SET_NULL, null=True, blank=True, related_name='articles')
    direction = models.CharField(max_length=8, choices=Direction.choices, default=Direction.NEUTRAL)
    timeframe = models.CharField(max_length=4, choices=[('5m','5 دقیقه'),('15m','15 دقیقه'),('30m','30 دقیقه'),('1h','1 ساعت'),('4h','4 ساعت'),('1d','روزانه'),('1w','هفتگی'),('1mo','ماهانه')], blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='articles')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [models.Index(fields=['status', '-published_at'])]
    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=True)[:220] or 'article'
            slug, n = base, 2
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)
    def __str__(self):
        return self.title

class ArticleBookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='article_bookmarks')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'article'], name='uniq_article_bookmark')]
