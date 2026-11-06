from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


DEFAULT_PRICE_ACTION_PROMPT = '''You are a cautious, evidence-driven technical market analyst specializing in Price Action. Analyze only the supplied OHLCV data and derived indicators. Do not claim certainty, promise profit, or provide personalized financial advice. Every market scenario must be conditional and include a clear invalidation condition. Return exactly one valid JSON object with these keys: market_trend, market_structure, price_action, support_resistance, liquidity_zones, bullish_scenario, bearish_scenario, entry_zone, stop_loss_invalidation, targets, confidence, risk_analysis, summary. Use concise but meaningful structured values. confidence must be an integer from 0 to 100 and must represent analytical confidence, not probability of profit. Explicitly state when data is insufficient. Keep bullish and bearish alternatives balanced. Never invent current prices, support/resistance levels, liquidity pools, or trade levels that cannot be derived from supplied data. Distinguish observed facts from hypotheses. Mention timeframe conflicts and stale or sparse data when relevant.'''


def seed_default_price_action_prompt(apps, schema_editor):
    PromptTemplate = apps.get_model('analyses', 'PromptTemplate')
    PromptTemplateRevision = apps.get_model('analyses', 'PromptTemplateRevision')
    template, created = PromptTemplate.objects.get_or_create(
        key='price-action-default',
        defaults={
            'purpose': 'price_action',
            'title': 'پرامپت اصلی تحلیل Price Action',
            'category': 'market_analysis',
            'description': 'قالب پیش‌فرض تحلیل سناریومحور بازار بر اساس داده‌های OHLCV ثبت‌شده در سامانه.',
            'system_prompt': DEFAULT_PRICE_ACTION_PROMPT,
            'user_prompt_template': '',
            'output_language': 'both',
            'model_override': '',
            'is_active': True,
            'is_default': True,
            'revision': 1,
        },
    )
    if created:
        PromptTemplateRevision.objects.get_or_create(
            template=template,
            revision_number=1,
            defaults={
                'key': template.key,
                'purpose': template.purpose,
                'title': template.title,
                'category': template.category,
                'description': template.description,
                'system_prompt': template.system_prompt,
                'user_prompt_template': template.user_prompt_template,
                'output_language': template.output_language,
                'model_override': template.model_override,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('analyses', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PromptTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.SlugField(help_text='فقط حروف انگلیسی کوچک، عدد و خط تیره؛ مانند price-action-pa-v1.', max_length=100, unique=True, verbose_name='شناسه یکتای قالب (انگلیسی)')),
                ('purpose', models.SlugField(db_index=True, help_text='برای Price Action مقدار price_action؛ برای کاربردهای دیگر شناسه‌ای مانند article_writer وارد کنید.', max_length=80, verbose_name='شناسه کاربرد (purpose)')),
                ('title', models.CharField(help_text='نام قابل مشاهده در پنل مدیریت و فرم تولید تحلیل؛ فارسی یا انگلیسی.', max_length=160, verbose_name='عنوان پرامپت')),
                ('category', models.CharField(choices=[('market_analysis', 'تحلیل بازار'), ('content', 'تولید محتوا'), ('research', 'پژوهش و بررسی'), ('risk', 'مدیریت ریسک'), ('education', 'آموزش'), ('general', 'عمومی'), ('custom', 'سفارشی')], default='custom', max_length=32, verbose_name='دسته‌بندی')),
                ('description', models.TextField(blank=True, help_text='توضیح داخلی درباره کاربرد و زمان استفاده از این پرامپت.', verbose_name='توضیحات داخلی')),
                ('system_prompt', models.TextField(help_text='دستور اصلی سیستم برای مدل هوش مصنوعی؛ می‌توانید متن فارسی، انگلیسی یا ترکیبی وارد کنید.', verbose_name='پرامپت اصلی (System Prompt)')),
                ('user_prompt_template', models.TextField(blank=True, help_text='متن ثابت اختیاری که همراه داده‌های درخواست به مدل ارسال می‌شود؛ در این نسخه جای‌گذاری متغیر انجام نمی‌شود.', verbose_name='دستور تکمیلی (User Instructions)')),
                ('output_language', models.CharField(choices=[('fa', 'فارسی'), ('en', 'English'), ('both', 'فارسی و انگلیسی')], default='both', max_length=8, verbose_name='زبان خروجی')),
                ('model_override', models.CharField(blank=True, help_text='در صورت خالی بودن از مدل پیش‌فرض فایل .env استفاده می‌شود.', max_length=100, verbose_name='مدل اختصاصی (اختیاری)')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='فعال')),
                ('is_default', models.BooleanField(default=False, help_text='با ذخیره این گزینه، قالب پیش‌فرض قبلی همین purpose به‌صورت خودکار از حالت پیش‌فرض خارج می‌شود.', verbose_name='قالب پیش‌فرض این کاربرد')),
                ('revision', models.PositiveIntegerField(default=1, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_prompt_templates', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_prompt_templates', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['purpose', '-is_default', 'title']},
        ),
        migrations.CreateModel(
            name='PromptTemplateRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('revision_number', models.PositiveIntegerField()),
                ('key', models.SlugField(max_length=100)),
                ('purpose', models.SlugField(max_length=80)),
                ('title', models.CharField(max_length=160)),
                ('category', models.CharField(max_length=32)),
                ('description', models.TextField(blank=True)),
                ('system_prompt', models.TextField()),
                ('user_prompt_template', models.TextField(blank=True)),
                ('output_language', models.CharField(max_length=8)),
                ('model_override', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='revisions', to='analyses.prompttemplate')),
            ],
            options={'ordering': ['-revision_number']},
        ),
        migrations.AddField(
            model_name='analysisrequest',
            name='prompt_template',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='analysis_runs', to='analyses.prompttemplate'),
        ),
        migrations.AddField(
            model_name='analysisrequest',
            name='prompt_revision',
            field=models.PositiveIntegerField(blank=True, help_text='نسخه قالبی که برای این تحلیل استفاده شده است.', null=True),
        ),
        migrations.AddConstraint(
            model_name='prompttemplaterevision',
            constraint=models.UniqueConstraint(fields=('template', 'revision_number'), name='uniq_prompt_template_revision'),
        ),
        migrations.RunPython(seed_default_price_action_prompt, migrations.RunPython.noop),
    ]
