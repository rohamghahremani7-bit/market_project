from django import forms

from marketdata.models import Symbol, Candle
from .models import AnalysisRequest, PromptTemplate


class AnalysisCreateForm(forms.Form):
    prompt_template = forms.ModelChoiceField(
        queryset=PromptTemplate.objects.none(),
        required=False,
        label='قالب پرامپت Price Action',
        help_text='قالب‌ها را مدیر سامانه در بخش مدیریت پرامپت‌ها می‌سازد. در صورت خالی بودن، قالب پیش‌فرض فعال استفاده می‌شود.',
    )
    symbol = forms.ModelChoiceField(queryset=Symbol.objects.filter(is_active=True), label='نماد')
    timeframe = forms.ChoiceField(choices=Candle.Timeframe.choices, label='تایم‌فریم')
    horizon = forms.ChoiceField(choices=AnalysisRequest.Horizon.choices, label='افق تحلیل')
    notes = forms.CharField(
        required=False,
        max_length=1200,
        label='توضیحات تکمیلی',
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'اختیاری: سطح یا رویداد خاصی که باید بررسی شود'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_templates = PromptTemplate.objects.filter(
            purpose='price_action', is_active=True
        ).order_by('-is_default', 'title')
        self.fields['prompt_template'].queryset = active_templates
        default_template = active_templates.filter(is_default=True).first()
        if default_template and not self.is_bound:
            self.fields['prompt_template'].initial = default_template.pk
