from django.contrib import admin, messages
from django.db import transaction
from django import forms

from .models import (
    AnalysisRequest,
    AnalysisVersion,
    AnalysisBookmark,
    AnalysisEvaluation,
    PromptTemplate,
    PromptTemplateRevision,
)


class AnalysisVersionInline(admin.TabularInline):
    model = AnalysisVersion
    extra = 0
    readonly_fields = ('version_number', 'result_snapshot', 'note', 'changed_by', 'created_at')
    can_delete = False


@admin.register(AnalysisRequest)
class AnalysisRequestAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'timeframe', 'horizon', 'status', 'confidence', 'prompt_template', 'created_by', 'created_at')
    list_filter = ('status', 'horizon', 'timeframe', 'symbol')
    search_fields = ('symbol__code', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'published_at', 'market_snapshot', 'prompt_snapshot', 'prompt_template', 'prompt_revision')
    inlines = [AnalysisVersionInline]


class PromptTemplateRevisionInline(admin.StackedInline):
    model = PromptTemplateRevision
    extra = 0
    can_delete = False
    show_change_link = True
    readonly_fields = (
        'revision_number', 'key', 'purpose', 'title', 'category', 'description',
        'system_prompt', 'user_prompt_template', 'output_language', 'model_override',
        'changed_by', 'created_at',
    )
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


class PromptTemplateAdminForm(forms.ModelForm):
    class Meta:
        model = PromptTemplate
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'system_prompt': forms.Textarea(attrs={'rows': 24, 'class': 'vLargeTextField', 'dir': 'auto'}),
            'user_prompt_template': forms.Textarea(attrs={'rows': 12, 'class': 'vLargeTextField', 'dir': 'auto'}),
        }


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    form = PromptTemplateAdminForm
    list_display = ('title', 'purpose', 'category', 'output_language', 'revision', 'is_active', 'is_default', 'updated_at')
    list_filter = ('purpose', 'category', 'output_language', 'is_active', 'is_default')
    search_fields = ('key', 'purpose', 'title', 'description', 'system_prompt', 'user_prompt_template')
    readonly_fields = ('revision', 'created_by', 'updated_by', 'created_at', 'updated_at')
    inlines = [PromptTemplateRevisionInline]
    ordering = ('purpose', '-is_default', 'title')
    fieldsets = (
        ('شناسه و کاربرد', {
            'fields': ('title', 'key', 'purpose', 'category', 'description'),
            'description': 'برای پرامپت تحلیل Price Action مقدار purpose را price_action بگذارید. برای کاربردهای دیگر شناسه‌ای مانند article_writer یا risk_review بسازید.'
        }),
        ('متن پرامپت', {
            'fields': ('system_prompt', 'user_prompt_template'),
            'description': 'متن‌ها می‌توانند فارسی، انگلیسی یا ترکیبی باشند. دستور تکمیلی اختیاری است.'
        }),
        ('خروجی و فعال‌سازی', {
            'fields': ('output_language', 'model_override', 'is_active', 'is_default')
        }),
        ('تاریخچه', {
            'fields': ('revision', 'created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        content_fields = (
            'key', 'purpose', 'title', 'category', 'description',
            'system_prompt', 'user_prompt_template', 'output_language', 'model_override',
        )
        previous = None
        if change and obj.pk:
            previous = PromptTemplate.objects.select_for_update().filter(pk=obj.pk).first()

        content_changed = bool(previous and any(
            getattr(previous, field) != getattr(obj, field) for field in content_fields
        ))
        if previous and content_changed:
            obj.revision = previous.revision + 1
        elif not previous:
            obj.revision = 1

        if not obj.is_active:
            obj.is_default = False
        if obj.is_default:
            # Keep a single default per purpose in the admin workflow.
            PromptTemplate.objects.filter(purpose=obj.purpose, is_default=True).exclude(pk=obj.pk).update(is_default=False)
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

        if not previous or content_changed:
            PromptTemplateRevision.objects.create(
                template=obj,
                revision_number=obj.revision,
                key=obj.key,
                purpose=obj.purpose,
                title=obj.title,
                category=obj.category,
                description=obj.description,
                system_prompt=obj.system_prompt,
                user_prompt_template=obj.user_prompt_template,
                output_language=obj.output_language,
                model_override=obj.model_override,
                changed_by=request.user,
            )
            if previous:
                self.message_user(request, f'نسخه {obj.revision} ذخیره شد؛ نسخه‌های قبلی در تاریخچه پایین صفحه حفظ شده‌اند.', messages.SUCCESS)

    def has_delete_permission(self, request, obj=None):
        # Deactivate old prompt templates instead of deleting templates referenced by historical runs.
        return False


@admin.register(PromptTemplateRevision)
class PromptTemplateRevisionAdmin(admin.ModelAdmin):
    list_display = ('template', 'revision_number', 'purpose', 'output_language', 'changed_by', 'created_at')
    list_filter = ('purpose', 'output_language', 'created_at')
    search_fields = ('template__title', 'template__key', 'system_prompt')
    readonly_fields = (
        'template', 'revision_number', 'key', 'purpose', 'title', 'category', 'description',
        'system_prompt', 'user_prompt_template', 'output_language', 'model_override', 'changed_by', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(AnalysisBookmark)
admin.site.register(AnalysisEvaluation)
