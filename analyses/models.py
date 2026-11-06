from django.conf import settings
from django.db import models
from django.utils import timezone

class PromptTemplate(models.Model):
    """Reusable, admin-managed prompts for different application workflows."""

    class Category(models.TextChoices):
        MARKET_ANALYSIS = 'market_analysis', 'تحلیل بازار'
        CONTENT = 'content', 'تولید محتوا'
        RESEARCH = 'research', 'پژوهش و بررسی'
        RISK = 'risk', 'مدیریت ریسک'
        EDUCATION = 'education', 'آموزش'
        GENERAL = 'general', 'عمومی'
        CUSTOM = 'custom', 'سفارشی'

    class OutputLanguage(models.TextChoices):
        PERSIAN = 'fa', 'فارسی'
        ENGLISH = 'en', 'English'
        BILINGUAL = 'both', 'فارسی و انگلیسی'

    # key identifies this concrete template; purpose groups alternatives for one workflow.
    key = models.SlugField(max_length=100, unique=True, verbose_name='شناسه یکتای قالب (انگلیسی)', help_text='فقط حروف انگلیسی کوچک، عدد و خط تیره؛ مانند price-action-pa-v1.')
    purpose = models.SlugField(max_length=80, db_index=True, verbose_name='شناسه کاربرد (purpose)', help_text='برای Price Action مقدار price_action؛ برای کاربردهای دیگر شناسه‌ای مانند article_writer وارد کنید.')
    title = models.CharField(max_length=160, verbose_name='عنوان پرامپت', help_text='نام قابل مشاهده در پنل مدیریت و فرم تولید تحلیل؛ فارسی یا انگلیسی.')
    category = models.CharField(max_length=32, choices=Category.choices, default=Category.CUSTOM, verbose_name='دسته‌بندی')
    description = models.TextField(blank=True, verbose_name='توضیحات داخلی', help_text='توضیح داخلی درباره کاربرد و زمان استفاده از این پرامپت.')
    system_prompt = models.TextField(verbose_name='پرامپت اصلی (System Prompt)', help_text='دستور اصلی سیستم برای مدل هوش مصنوعی؛ می‌توانید متن فارسی، انگلیسی یا ترکیبی وارد کنید.')
    user_prompt_template = models.TextField(blank=True, verbose_name='دستور تکمیلی (User Instructions)', help_text='متن ثابت اختیاری که همراه داده‌های درخواست به مدل ارسال می‌شود؛ در این نسخه جای‌گذاری متغیر انجام نمی‌شود.')
    output_language = models.CharField(max_length=8, choices=OutputLanguage.choices, default=OutputLanguage.BILINGUAL, verbose_name='زبان خروجی')
    model_override = models.CharField(max_length=100, blank=True, verbose_name='مدل اختصاصی (اختیاری)', help_text='در صورت خالی بودن از مدل پیش‌فرض فایل .env استفاده می‌شود.')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='فعال')
    is_default = models.BooleanField(default=False, verbose_name='قالب پیش‌فرض این کاربرد', help_text='با ذخیره این گزینه، قالب پیش‌فرض قبلی همین purpose به‌صورت خودکار از حالت پیش‌فرض خارج می‌شود.')
    revision = models.PositiveIntegerField(default=1, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_prompt_templates')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_prompt_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['purpose', '-is_default', 'title']

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.system_prompt.strip():
            raise ValidationError({'system_prompt': 'متن پرامپت اصلی نمی‌تواند خالی باشد.'})

    def __str__(self):
        suffix = ' (پیش‌فرض)' if self.is_default else ''
        return f'{self.title} — {self.purpose}{suffix}'


class PromptTemplateRevision(models.Model):
    """Immutable snapshot of each saved prompt-template revision."""
    template = models.ForeignKey(PromptTemplate, on_delete=models.CASCADE, related_name='revisions')
    revision_number = models.PositiveIntegerField()
    key = models.SlugField(max_length=100)
    purpose = models.SlugField(max_length=80)
    title = models.CharField(max_length=160)
    category = models.CharField(max_length=32)
    description = models.TextField(blank=True)
    system_prompt = models.TextField()
    user_prompt_template = models.TextField(blank=True)
    output_language = models.CharField(max_length=8)
    model_override = models.CharField(max_length=100, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-revision_number']
        constraints = [
            models.UniqueConstraint(fields=['template', 'revision_number'], name='uniq_prompt_template_revision'),
        ]

    def __str__(self):
        return f'{self.template.title} — نسخه {self.revision_number}'


class AnalysisRequest(models.Model):
    class Horizon(models.TextChoices):
        H24 = '24h', '۲۴ ساعت آینده'
        W1 = '1w', 'یک هفته آینده'
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'پیش‌نویس'
        PENDING_REVIEW = 'PENDING_REVIEW', 'در انتظار بازبینی'
        PUBLISHED = 'PUBLISHED', 'منتشرشده'
        FAILED = 'FAILED', 'ناموفق'
    symbol = models.ForeignKey('marketdata.Symbol', on_delete=models.PROTECT, related_name='analyses')
    timeframe = models.CharField(max_length=4, choices=[('5m','5 دقیقه'),('15m','15 دقیقه'),('30m','30 دقیقه'),('1h','1 ساعت'),('4h','4 ساعت'),('1d','روزانه'),('1w','هفتگی'),('1mo','ماهانه')])
    horizon = models.CharField(max_length=3, choices=Horizon.choices, default=Horizon.H24)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    model_name = models.CharField(max_length=100, blank=True)
    provider = models.CharField(max_length=40, default='openai')
    prompt_snapshot = models.TextField(blank=True)
    prompt_template = models.ForeignKey('analyses.PromptTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='analysis_runs')
    prompt_revision = models.PositiveIntegerField(null=True, blank=True, help_text='نسخه قالبی که برای این تحلیل استفاده شده است.')
    market_snapshot = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    confidence = models.PositiveSmallIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='generated_analyses')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_analyses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', '-created_at'])]
    def __str__(self):
        return f'{self.symbol.code} {self.timeframe} / {self.get_horizon_display()}'

class AnalysisVersion(models.Model):
    analysis = models.ForeignKey(AnalysisRequest, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    result_snapshot = models.JSONField(default=dict)
    note = models.CharField(max_length=240, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-version_number']
        constraints = [models.UniqueConstraint(fields=['analysis', 'version_number'], name='uniq_analysis_version')]

class AnalysisBookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analysis_bookmarks')
    analysis = models.ForeignKey(AnalysisRequest, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'analysis'], name='uniq_analysis_bookmark')]

class AnalysisEvaluation(models.Model):
    class Horizon(models.TextChoices):
        H24 = '24h', 'پس از ۲۴ ساعت'
        W1 = '1w', 'پس از یک هفته'
    analysis = models.ForeignKey(AnalysisRequest, on_delete=models.CASCADE, related_name='evaluations')
    horizon = models.CharField(max_length=3, choices=Horizon.choices)
    reference_price = models.DecimalField(max_digits=24, decimal_places=8)
    evaluated_price = models.DecimalField(max_digits=24, decimal_places=8)
    return_percent = models.DecimalField(max_digits=12, decimal_places=5)
    direction_match = models.BooleanField(null=True, blank=True)
    evaluated_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=240, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['analysis', 'horizon'], name='uniq_analysis_evaluation')]
        ordering = ['-evaluated_at']
