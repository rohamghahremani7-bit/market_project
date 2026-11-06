from django import forms
from .models import Symbol, Candle

class CsvImportForm(forms.Form):
    symbol = forms.ModelChoiceField(queryset=Symbol.objects.filter(is_active=True), label='نماد')
    timeframe = forms.ChoiceField(choices=Candle.Timeframe.choices, label='تایم‌فریم')
    file = forms.FileField(label='فایل CSV')
