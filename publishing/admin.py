from django.contrib import admin
from django.utils import timezone
from .models import Article, ArticleBookmark

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'symbol', 'direction', 'status', 'author', 'published_at')
    list_filter = ('status', 'direction', 'timeframe', 'symbol')
    search_fields = ('title', 'body', 'symbol__code', 'author__username')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['publish_selected']
    @admin.action(description='انتشار مطالب انتخاب‌شده')
    def publish_selected(self, request, queryset):
        queryset.update(status=Article.Status.PUBLISHED, published_at=timezone.now())

admin.site.register(ArticleBookmark)
