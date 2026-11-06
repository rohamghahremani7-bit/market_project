from django import forms
from .models import Article

class ArticleForm(forms.ModelForm):
    publication_choice = forms.ChoiceField(
        choices=(('DRAFT', 'ذخیره به‌صورت پیش‌نویس'), ('PUBLISH', 'درخواست انتشار')),
        label='وضعیت مطلب', initial='PUBLISH')
    class Meta:
        model = Article
        fields = ('title', 'excerpt', 'body', 'image', 'symbol', 'direction', 'timeframe')
        labels = {'title':'عنوان مطلب', 'excerpt':'خلاصه کوتاه', 'body':'متن مطلب', 'image':'تصویر',
                  'symbol':'نماد', 'direction':'جهت بازار', 'timeframe':'تایم‌فریم'}
        widgets = {'body': forms.Textarea(attrs={'rows': 12}), 'excerpt': forms.Textarea(attrs={'rows': 2})}
