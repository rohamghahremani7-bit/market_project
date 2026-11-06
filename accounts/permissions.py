from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

def operator_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_operator:
            messages.error(request, 'برای دسترسی به این بخش مجوز اپراتور لازم است.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped

def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_admin_role:
            messages.error(request, 'این عملیات فقط برای مدیر سامانه مجاز است.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped
