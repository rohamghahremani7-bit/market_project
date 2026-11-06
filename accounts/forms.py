from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='ایمیل')
    display_name = forms.CharField(max_length=120, required=False, label='نام نمایشی')
    class Meta:
        model = User
        fields = ('username', 'display_name', 'email', 'password1', 'password2')
        labels = {'username': 'نام کاربری', 'password1': 'رمز عبور', 'password2': 'تکرار رمز عبور'}

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('display_name', 'email', 'bio')
        labels = {'display_name': 'نام نمایشی', 'email': 'ایمیل', 'bio': 'درباره من'}
        widgets = {'bio': forms.Textarea(attrs={'rows': 4})}

class RoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('role', 'is_active')
        labels = {'role': 'نقش کاربر', 'is_active': 'حساب فعال'}
